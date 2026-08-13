"""Jahresabschluss-Prüfpipeline auf DATEV-Buchungsstapeln (CLI).

Aufruf:
  py werkzeuge\\ja_pruefung.py --stapel <Datei/Ordner> [weitere ...]
     [--susa susa.csv] [--opos opos.csv] [--kontenbeschriftung kb.csv]
     [--skr auto|03|04] [--config konten_config.json]
     [--ausgabe ordner] [--mandant name]

Erzeugt: Pruefbericht_<Mandant>_<Jahr>.xlsx, befunde.json,
llm_kandidaten.json (Eingabe fuer die KI-Beurteilungsschicht).
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import bilanz
from befunde import KATALOG_NAMEN, RANG, Kontext, eur
from checks import ALLE_FACHLICH
from checks_erweitert import ALLE_ERWEITERT
from checks_vorjahr import ALLE_VORJAHR
from datev_parser import (lies_buchungsstapel, lies_header,
                          lies_kontenbeschriftungen, lies_opos, lies_susa)
from excel_report import schreibe_bericht
from kontenplan import Kontenplan, erkenne_skr
from statistik import ALLE_STATISTIK

VERSION = "0.2.0"


def sammle_dateien(pfade: list[str]) -> list[Path]:
    dateien: list[Path] = []
    for p in pfade:
        pfad = Path(p)
        if pfad.is_dir():
            dateien += sorted(f for f in pfad.glob("*.csv"))
        elif pfad.exists():
            dateien.append(pfad)
        else:
            print(f"WARNUNG: {p} nicht gefunden", file=sys.stderr)
    return dateien


def baue_llm_kandidaten(ctx: Kontext, befunde) -> list[dict]:
    je_quelle = {f"{b.quelle}:{b.zeile}": b for b in ctx.buchungen}
    kandidaten: dict[str, dict] = {}

    def _neu(schluessel: str, grund: str, b=None, befund=None) -> None:
        if schluessel in kandidaten:
            if grund not in kandidaten[schluessel]["grund"]:
                kandidaten[schluessel]["grund"] += f"; {grund}"
            return
        if b is not None:
            eintrag = {
                "grund": grund, "konto": b.konto,
                "konto_name": ctx.name(b.konto), "gegenkonto": b.gegenkonto,
                "gegenkonto_name": ctx.name(b.gegenkonto),
                "datum": b.belegdatum.isoformat() if b.belegdatum else None,
                "betrag": float(b.umsatz), "bu": b.bu, "beleg": b.belegfeld1,
                "buchungstext": b.buchungstext,
                "quelle": f"{b.quelle}:{b.zeile}",
            }
        else:
            eintrag = {
                "grund": grund, "konto": befund.konto,
                "konto_name": ctx.name(befund.konto) if befund.konto else "",
                "gegenkonto": None, "gegenkonto_name": "",
                "datum": befund.datum.isoformat() if befund.datum else None,
                "betrag": float(befund.betrag) if befund.betrag is not None else None,
                "bu": "", "beleg": befund.beleg,
                "buchungstext": befund.buchungstext or befund.text,
                "quelle": befund.quelle,
            }
        kandidaten[schluessel] = eintrag

    for f in befunde:
        if not f.llm_kandidat:
            continue
        quelle = f.quelle.split(" / ")[-1] if f.quelle else ""
        b = je_quelle.get(quelle)
        grund = f"{f.check_id} {f.check_name}"
        _neu(quelle or f"befund:{id(f)}", grund, b=b, befund=f)

    min_eur = Decimal(str(ctx.param["llm_kandidat_min_eur"]))
    for b in ctx.buchungen:
        if ctx.ist_eb(b):
            continue
        guv = b.konto if ctx.plan.ist_guv(b.konto) else (
            b.gegenkonto if ctx.plan.ist_guv(b.gegenkonto) else None)
        if guv is None or not ctx.plan.in_gruppe(guv, "sachfremd_llm"):
            continue
        if ctx.plan.netto(b) < min_eur:
            continue
        _neu(f"{b.quelle}:{b.zeile}",
             "Kontenbereich mit erhöhtem Kontierungs-/Privatrisiko", b=b)

    geordnet = sorted(kandidaten.values(),
                      key=lambda k: -(k["betrag"] or 0))
    gesamt = len(geordnet)
    maximal = int(ctx.param["llm_kandidaten_max"])
    if maximal and gesamt > maximal:
        # Deckel ist optionale Kostenbremse - nie still kappen
        ctx.kennzahlen["KI-Kandidaten: Deckel aktiv"] = (
            f"{maximal} von {gesamt} exportiert (Betrags-Priorisierung); "
            "'llm_kandidaten_max' = 0 hebt den Deckel auf")
        geordnet = geordnet[:maximal]
    for i, k in enumerate(geordnet, start=1):
        geordnet[i - 1] = {"id": f"K{i:03d}", **k}
    return geordnet, gesamt


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="JA-Prüfung auf DATEV-Buchungsstapeln")
    p.add_argument("--stapel", nargs="+", required=True,
                   help="Buchungsstapel-Dateien oder Ordner (EXTF/DTVF-CSV)")
    p.add_argument("--susa", help="Summen- und Saldenliste (CSV: Konto;Saldo)")
    p.add_argument("--susa-vorjahr", dest="susa_vorjahr",
                   help="SuSa des Vorjahres (CSV: Konto;Saldo) für EB-Abgleich "
                        "und GuV-Vorjahresvergleich")
    p.add_argument("--opos", help="OPOS-Liste (CSV: Konto;Betrag;Datum/Fälligkeit)")
    p.add_argument("--kontenplan", "--kontenbeschriftung",
                   dest="kontenbeschriftung",
                   help="Kontenplan des Mandanten (DATEV-Export "
                        "'Kontenbeschriftungen', EXTF Kat. 20: alle "
                        "angelegten Konten mit Bezeichnung)")
    p.add_argument("--skr", choices=["auto", "03", "04"], default="auto")
    p.add_argument("--rechtsform",
                   choices=["einzelunternehmen", "personengesellschaft",
                            "kapitalgesellschaft"],
                   help="steuert rechtsformabhängige Checks (PP-01/02/04, "
                        "SB-10); ohne Angabe gilt Parameter 'rechtsform' "
                        "aus der Konfiguration")
    p.add_argument("--config", default=str(Path(__file__).parent / "konten_config.json"))
    p.add_argument("--ausgabe", help="Ausgabeordner (Default: <Stapelordner>/JA-Pruefung)")
    p.add_argument("--mandant", help="Mandantenbezeichnung für Bericht/Dateiname")
    p.add_argument("--pbi", action="store_true",
                   help="zusätzlich ein Power-BI-Projekt (PBIP) im "
                        "Ausgabeordner erzeugen (öffnen mit Power BI Desktop; "
                        "Datenquelle = befunde.csv über Parameter "
                        "'BefundeCsvPfad')")
    args = p.parse_args(argv)

    dateien = sammle_dateien(args.stapel)
    infos, buchungen, warnungen = [], [], []
    namen: dict[int, str] = {}
    for f in dateien:
        header = lies_header(f)
        if header.kennzeichen not in ("EXTF", "DTVF"):
            continue
        if header.kategorie == 20:
            namen.update(lies_kontenbeschriftungen(f))
            continue
        if header.kategorie != 21:
            warnungen.append(f"{f.name}: Formatkategorie {header.kategorie} übersprungen")
            continue
        info, bs, ws = lies_buchungsstapel(f)
        infos.append(info)
        buchungen += bs
        warnungen += ws
    if args.kontenbeschriftung:
        namen.update(lies_kontenbeschriftungen(args.kontenbeschriftung))
    if not buchungen:
        print("FEHLER: keine Buchungen gelesen (Buchungsstapel im "
              "DATEV-Format, Kategorie 21, erwartet).", file=sys.stderr)
        return 2

    skl = max(i.sachkontenlaenge for i in infos)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.rechtsform:
        cfg["parameter"]["rechtsform"] = args.rechtsform
    if args.skr == "auto":
        skr, skr_text = erkenne_skr(buchungen, skl)
    else:
        skr, skr_text = args.skr, f"SKR{args.skr} (vorgegeben)"
    plan = Kontenplan(cfg, skr, skl)
    susa = lies_susa(args.susa) if args.susa else None
    susa_vj = lies_susa(args.susa_vorjahr) if args.susa_vorjahr else None
    opos = lies_opos(args.opos) if args.opos else None
    if args.susa and not susa:
        warnungen.append(f"{args.susa}: keine SuSa-Daten erkannt (Spalten Konto/Saldo)")
        susa = None
    if args.susa_vorjahr and not susa_vj:
        warnungen.append(f"{args.susa_vorjahr}: keine SuSa-Daten erkannt "
                         "(Spalten Konto/Saldo)")
        susa_vj = None
    if args.opos and not opos:
        warnungen.append(f"{args.opos}: keine OPOS-Daten erkannt (Spalten Konto/Betrag)")
        opos = None

    mandant = args.mandant or infos[0].mandant or "Mandant"
    ctx = Kontext(buchungen, plan, cfg["parameter"], infos, namen, susa,
                  opos, warnungen, susa_vj=susa_vj, mandant_name=mandant)
    volumen = sum((b.umsatz for b in buchungen), Decimal(0))
    ctx.kennzahlen["Buchungen / bebuchte Konten"] = (
        f"{len(buchungen)} / {len(ctx.anzahl)}")
    ctx.kennzahlen["Buchungsvolumen (Summe Umsätze)"] = f"{eur(volumen)} EUR"
    if namen:
        bebucht_mit = sum(1 for k in ctx.anzahl if k in namen)
        ohne_anlage = sum(1 for k in ctx.anzahl if k not in namen
                          and not plan.in_gruppe(k, "saldovortrag"))
        ctx.kennzahlen["Kontenplan (Kontenbeschriftungen Kat. 20)"] = (
            f"{len(namen)} Konten angelegt, {bebucht_mit} davon bebucht; "
            f"{ohne_anlage} bebucht ohne Anlage (siehe DV-03)")
    if not ctx.eb_vorhanden:
        ctx.kennzahlen["EB-Werte"] = ("nicht im Stapel enthalten – "
                                      "Bestandschecks nur auf Bewegungsbasis")
    erloese = -sum((ctx.saldo_netto[k] for k in ctx.anzahl
                    if plan.in_gruppe(k, "ertrag")
                    or plan.in_gruppe(k, "erloesschmaelerung")), Decimal(0))
    if erloese > 0:
        ctx.kennzahlen["Erlöse netto (rechnerisch)"] = f"{eur(erloese)} EUR"
        if susa_vj:
            erloese_vj = -sum((s for k, s in susa_vj.items()
                               if plan.in_gruppe(k, "ertrag")
                               or plan.in_gruppe(k, "erloesschmaelerung")),
                              Decimal(0))
            if erloese_vj > 0:
                delta = float((erloese - erloese_vj) / erloese_vj)
                ctx.kennzahlen["Erlöse netto Vorjahr (SuSa)"] = (
                    f"{eur(erloese_vj)} EUR (Veränderung {delta:+.1%})")
        material = sum((ctx.saldo_netto[k] for k in ctx.anzahl
                        if plan.in_gruppe(k, "material")), Decimal(0))
        if material > 0:
            ctx.kennzahlen["Rohertrag (rechnerisch)"] = (
                f"{eur(erloese - material)} EUR "
                f"({float((erloese - material) / erloese):.1%})")
        for label, gruppe in (("Materialquote", "material"),
                              ("Personalquote", "lohn"),
                              ("Mietkostenquote", "raumkosten"),
                              ("Werbekostenquote", "werbekosten")):
            aufwand = sum((ctx.saldo_netto[k] for k in ctx.anzahl
                           if plan.in_gruppe(k, gruppe)), Decimal(0))
            if aufwand > 0:
                ctx.kennzahlen[label] = (f"{float(aufwand / erloese):.1%} "
                                         f"({eur(aufwand)} EUR)")
        if cfg["parameter"].get("rechtsform") == "kapitalgesellschaft":
            aktiva = sum((s for k, s in ctx.saldo_netto.items()
                          if s > 0 and not plan.ist_guv(k)
                          and not plan.in_gruppe(k, "saldovortrag")),
                         Decimal(0))
            ctx.kennzahlen["Größenklassen-Indikation (§ 267, § 267a HGB)"] = (
                f"Bilanzsumme näherungsweise {eur(aktiva)} EUR, Umsatzerlöse "
                f"{eur(erloese)} EUR; Einstufung erfordert zusätzlich die "
                "Ø-Arbeitnehmerzahl (Schwellen: Kleinst 450 T€/900 T€, "
                "klein 7,5 Mio €/15 Mio €)")

    befunde = []
    for check in ALLE_FACHLICH + ALLE_ERWEITERT + ALLE_VORJAHR + ALLE_STATISTIK:
        befunde += check(ctx)
    befunde.sort(key=lambda f: (RANG[f.schwere], f.check_id))
    kandidaten, kandidaten_gesamt = baue_llm_kandidaten(ctx, befunde)

    erste = Path(dateien[0])
    ausgabe = Path(args.ausgabe) if args.ausgabe else erste.parent / "JA-Pruefung"
    ausgabe.mkdir(parents=True, exist_ok=True)
    mandant_datei = "".join(c for c in mandant if c.isalnum() or c in "-_") or "Mandant"
    jahr = ctx.datum_von.year if ctx.datum_von else ""
    zeitraum = "unbekannt"
    if ctx.datum_von and ctx.datum_bis:
        zeitraum = f"{ctx.datum_von:%d.%m.%Y} – {ctx.datum_bis:%d.%m.%Y}"

    rechtsform = cfg["parameter"].get("rechtsform", "unbekannt")
    meta = {
        "Mandant": mandant,
        "Rechtsform": rechtsform if rechtsform not in ("", "unbekannt") else (
            "NICHT ANGEGEBEN – rechtsformabhängige Prüfungen eingeschränkt "
            "(--rechtsform setzen; siehe DQ-02)"),
        "Berater / Bezeichnung": f"{infos[0].berater} / {infos[0].bezeichnung}",
        "Zeitraum": zeitraum,
        "Kontenrahmen": f"{skr_text}, Sachkontenlänge {skl}",
        "Quelldateien": ", ".join(sorted({i.quelle and Path(i.quelle).name for i in infos})),
        "Zusatzquellen": ", ".join(filter(None, (
            args.susa and f"SuSa: {Path(args.susa).name}",
            args.susa_vorjahr and f"Vorjahres-SuSa: {Path(args.susa_vorjahr).name}",
            args.opos and f"OPOS: {Path(args.opos).name}"))) or "keine",
        "Erstellt": f"{datetime.now():%d.%m.%Y %H:%M} – JA-Agent v{VERSION}",
    }
    xlsx = ausgabe / f"Pruefbericht_{mandant_datei}_{jahr}.xlsx"
    schreibe_bericht(xlsx, ctx, befunde, kandidaten, meta)

    (ausgabe / "befunde.json").write_text(json.dumps({
        "meta": meta, "kennzahlen": ctx.kennzahlen,
        "nicht_pruefbar": ctx.geskippt,
        "befunde": [f.as_dict() for f in befunde],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    # Flache CSV als Datenbasis fuer Power BI / Pivot-Auswertungen
    csv_pfad = ausgabe / "befunde.csv"
    felder = ["check_id", "check", "bereich", "ebene", "klasse", "schwere",
              "konto", "gegenkonto", "datum", "betrag", "beleg",
              "buchungstext", "text", "empfehlung", "quelle", "llm_kandidat"]
    with csv_pfad.open("w", encoding="utf-8-sig", newline="") as fh:
        schreiber = csv.DictWriter(fh, fieldnames=felder, delimiter=";")
        schreiber.writeheader()
        for f in befunde:
            schreiber.writerow(f.as_dict())
    salden_pfad = ausgabe / "salden.csv"
    with salden_pfad.open("w", encoding="utf-8-sig", newline="") as fh:
        schreiber = csv.writer(fh, delimiter=";")
        schreiber.writerow(["konto", "bezeichnung", "gruppen", "soll",
                            "haben", "saldo", "saldo_netto",
                            "saldo_vorjahr", "buchungen", "position"])
        for k in sorted(ctx.anzahl):
            vj = ctx.susa_vj.get(k) if ctx.susa_vj else None
            schreiber.writerow([
                k, ctx.name(k), ", ".join(plan.gruppen_von(k)),
                float(ctx.soll[k]), float(ctx.haben[k]),
                float(ctx.saldo[k]), float(ctx.saldo_netto[k]),
                float(vj) if vj is not None else "",
                ctx.anzahl[k], bilanz.position(ctx, k)])
        if ctx.vst_rechnerisch is not None:
            schreiber.writerow([
                "(implizit-vst)", "Vorsteuer rechnerisch (implizit)", "",
                "", "", "", float(ctx.vst_rechnerisch), "", 0,
                "E. Sonstige Aktiva"])
            schreiber.writerow([
                "(implizit-ust)", "Umsatzsteuer rechnerisch (implizit)", "",
                "", "", "", -float(ctx.ust_rechnerisch), "", 0,
                "C.IV. Sonstige Verbindlichkeiten"])
    pbi_ordner = None
    if args.pbi:
        vorlage = Path(__file__).parent / "pbi_vorlage"
        pbi_ordner = ausgabe / "PowerBI"
        if pbi_ordner.exists():
            shutil.rmtree(pbi_ordner)
        shutil.copytree(vorlage, pbi_ordner)
        bim = pbi_ordner / "JA-Pruefbericht.SemanticModel" / "model.bim"
        bim.write_text(
            bim.read_text(encoding="utf-8")
            .replace("__CSV_PFAD__",
                     str(csv_pfad.resolve()).replace("\\", "\\\\"))
            .replace("__SALDEN_PFAD__",
                     str(salden_pfad.resolve()).replace("\\", "\\\\")),
            encoding="utf-8")
    kandidaten_pfad = ausgabe / "llm_kandidaten.json"
    kandidaten_pfad.write_text(json.dumps({
        "hinweis": ("Kandidaten für die KI-Beurteilung. Ausgabeformat: "
                    "llm_beurteilung.json gemäß Skill ja-pruefung."),
        "kandidaten_gesamt": kandidaten_gesamt,
        "exportiert": len(kandidaten),
        "kandidaten": kandidaten,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    zaehler = Counter(f.schwere for f in befunde)
    print(f"JA-Prüfung v{VERSION} ({len(KATALOG_NAMEN)} Checks) | "
          f"{mandant} | {zeitraum} | {skr_text} | "
          f"{len(buchungen)} Buchungen aus {len(infos)} Stapel(n)")
    deckel = (f" (von {kandidaten_gesamt}, Deckel aktiv)"
              if kandidaten_gesamt > len(kandidaten) else "")
    print(f"Befunde: {zaehler.get('hoch', 0)} hoch / "
          f"{zaehler.get('mittel', 0)} mittel / "
          f"{zaehler.get('hinweis', 0)} Hinweise | "
          f"KI-Kandidaten: {len(kandidaten)}{deckel}")
    for schwere in ("hoch", "mittel", "hinweis"):
        zaehlung = Counter(f.check_id for f in befunde if f.schwere == schwere)
        if zaehlung:
            print(f"  {schwere:7s}: " + "; ".join(
                f"{cid} {KATALOG_NAMEN.get(cid, cid)} ({anz})"
                for cid, anz in sorted(zaehlung.items())))
    if rechtsform in ("", "unbekannt"):
        print("  WARNUNG: Rechtsform nicht angegeben (--rechtsform) – "
              "rechtsformabhängige Prüfungen laufen eingeschränkt (DQ-02).")
    if ctx.geskippt:
        print("  zusätzliche Prüfungen (Daten/Voraussetzung): " + "; ".join(
            f"{cid} ({grund})" for cid, grund in ctx.geskippt.items()))
    print(f"Bericht: {xlsx}")
    print(f"JSON:    {ausgabe / 'befunde.json'} | {kandidaten_pfad}")
    if pbi_ordner:
        print(f"PowerBI: {pbi_ordner / 'JA-Pruefbericht.pbip'} "
              "(mit Power BI Desktop öffnen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
