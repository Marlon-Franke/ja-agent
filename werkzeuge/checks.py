"""Fachliche deterministische Checks: Salden, AfA, USt/VSt,
Ausgangsrechnungen, OPOS, Personal/Privat.

Jede Funktion nimmt den Kontext und liefert eine Befundliste.
Nicht durchführbare Checks werden mit Grund als "geskippt" markiert
(Ausweis im Bericht), damit 0 Befunde von "nicht geprüft" unterscheidbar
bleiben.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal

from befunde import Befund, Kontext, eur


def _b(ctx: Kontext, cid: str, schwere: str, text: str, empfehlung: str = "",
       konto=None, gegenkonto=None, datum=None, betrag=None, beleg="",
       buchungstext="", quelle="", llm=False) -> Befund:
    if betrag is not None:
        betrag = Decimal(betrag).quantize(Decimal("0.01"))
    return Befund(check_id=cid, schwere=schwere, text=text,
                  empfehlung=empfehlung, konto=konto, gegenkonto=gegenkonto,
                  datum=datum, betrag=betrag, beleg=beleg,
                  buchungstext=buchungstext, quelle=quelle, llm_kandidat=llm)


def _q(b) -> str:
    return f"{b.quelle}:{b.zeile}"


def _limit(ctx: Kontext) -> int:
    return int(ctx.param["liste_max_je_check"])


def _rest(ctx: Kontext, out: list, cid: str, uebrig: int, einheit: str) -> None:
    """Kein stilles Kappen: über dem Listenlimit wird der Rest ausgewiesen."""
    if uebrig > 0:
        out.append(_b(ctx, cid, "hinweis",
            f"… {uebrig} weitere {einheit} über dem Listenlimit "
            f"({_limit(ctx)} je Check) nicht einzeln gelistet.",
            "Parameter 'liste_max_je_check' erhöhen, um die vollständige "
            "Liste auszugeben."))


# ---------------------------------------------------------------- Salden

def sb_01_negative_kasse(ctx: Kontext) -> list[Befund]:
    out = []
    for k in ctx.konten_in("kasse"):
        kum = Decimal(0)
        minimum, min_datum, erster_neg = Decimal(0), None, None
        for datum, _zeile, wert, _b_ in ctx.bewegungen[k]:
            kum += wert
            if kum < minimum:
                minimum, min_datum = kum, datum
            if kum < -ctx.bagatelle and erster_neg is None:
                erster_neg = datum
        if erster_neg is not None:
            out.append(_b(ctx, "SB-01", "hoch",
                f"Kassenkonto {ctx.kontotext(k)}: Saldo wird erstmals am "
                f"{erster_neg:%d.%m.%Y} negativ (Tiefststand {eur(minimum)} EUR"
                f"{f' am {min_datum:%d.%m.%Y}' if min_datum else ''}).",
                "Kassenbuch und Zählprotokolle abstimmen; fehlende Einlagen/"
                "Erlöse klären (§ 146 AO, Schätzungsrisiko § 162 AO).",
                konto=k, datum=erster_neg, betrag=minimum))
    return out


_ERWARTUNG = [  # (Gruppe, erwartetes Vorzeichen des Saldos, netto verwenden)
    ("av_abnutzbar", 1, False), ("av_nicht_abnutzbar", 1, False),
    ("gwg", 1, False), ("forderungen_sammel", 1, False),
    ("ertrag", -1, True), ("erloesschmaelerung", 1, True),
    ("aufwand", 1, True),
]
_SB02_AUSGESCHLOSSEN = ("kasse", "geldtransit", "interim", "steuer_vst",
                        "steuer_ust", "steuer_vz", "saldovortrag", "privat",
                        "bank")


def sb_02_saldenvorzeichen(ctx: Kontext) -> list[Befund]:
    out = []
    for k in sorted(ctx.anzahl):
        if not ctx.plan.ist_sachkonto(k):
            continue
        if any(ctx.plan.in_gruppe(k, g) for g in _SB02_AUSGESCHLOSSEN):
            continue
        for gruppe, vz, netto in _ERWARTUNG:
            if ctx.plan.in_gruppe(k, gruppe):
                saldo = ctx.saldo_netto[k] if netto else ctx.saldo[k]
                if saldo * vz < -ctx.bagatelle:
                    seite = "Soll" if vz > 0 else "Haben"
                    out.append(_b(ctx, "SB-02", "mittel",
                        f"Konto {ctx.kontotext(k)}: Saldo {eur(saldo)} EUR "
                        f"entgegen erwartetem {seite}-Saldo "
                        f"(Kontengruppe {gruppe}).",
                        "Fehlbuchungen, Stornierungen oder Umgliederungsbedarf "
                        "prüfen.", konto=k, betrag=saldo))
                break
    return out


def sb_03_geldtransit(ctx: Kontext) -> list[Befund]:
    return _nicht_ausgeglichen(ctx, "SB-03", "geldtransit",
        "Geldtransit muss sich zum Stichtag ausgleichen; offene Beträge "
        "(Einzahlung unterwegs?) aufklären.")


def sb_04_interim(ctx: Kontext) -> list[Befund]:
    return _nicht_ausgeglichen(ctx, "SB-04", "interim",
        "Interims-/Verrechnungs- und durchlaufende Konten zum Stichtag "
        "auflösen bzw. umgliedern.")


def _nicht_ausgeglichen(ctx: Kontext, cid: str, gruppe: str, empf: str) -> list[Befund]:
    out = []
    for k in ctx.konten_in(gruppe):
        saldo = ctx.saldo[k]
        if abs(saldo) > ctx.bagatelle:
            out.append(_b(ctx, cid, "mittel",
                f"Konto {ctx.kontotext(k)}: Restsaldo {eur(saldo)} EUR "
                f"zum Ende des Zeitraums.", empf, konto=k, betrag=saldo))
    return out


def sb_05_susa_abgleich(ctx: Kontext) -> list[Befund]:
    if ctx.susa is None:
        ctx.skip("SB-05", "erfordert SuSa (--susa)")
        return []
    out = []
    toleranz = Decimal(str(ctx.param["susa_toleranz_eur"]))
    nur_einseitig = 0
    for k in sorted(set(ctx.susa) | set(ctx.saldo)):
        if ctx.plan.ist_guv(k) or ctx.plan.in_gruppe(k, "steuer_vst") \
                or ctx.plan.in_gruppe(k, "steuer_ust") or ctx.plan.in_gruppe(k, "saldovortrag"):
            continue  # Stapel-Bruttowerte/implizite Steuer nicht vergleichbar
        if k not in ctx.susa or k not in ctx.saldo:
            nur_einseitig += 1
            continue
        # Netto-Sicht: FIBU bucht AV-Zugänge netto, der Stapel brutto
        diff = ctx.saldo_netto[k] - ctx.susa[k]
        if abs(diff) > toleranz:
            out.append(_b(ctx, "SB-05", "hinweis",
                f"Konto {ctx.kontotext(k)}: Saldo laut Stapel (steuerbereinigt) "
                f"{eur(ctx.saldo_netto[k])} EUR, "
                f"laut SuSa {eur(ctx.susa[k])} EUR (Differenz {eur(diff)} EUR).",
                "Vollständigkeit des Stapel-Exports (alle Monate, inkl. EB) "
                "und manuelle Korrekturen prüfen.", konto=k, betrag=diff))
    if nur_einseitig:
        out.append(_b(ctx, "SB-05", "hinweis",
            f"{nur_einseitig} Bestandskonten nur in einer der beiden Quellen "
            "(Stapel vs. SuSa) vorhanden.",
            "Exportumfang abgleichen."))
    return out


def sb_06_eb_differenz(ctx: Kontext) -> list[Befund]:
    if not ctx.eb_vorhanden:
        ctx.skip("SB-06", "keine EB-/Saldovortragsbuchungen im Stapel")
        return []
    summe = sum((ctx.saldo[k] for k in ctx.konten_in("saldovortrag")), Decimal(0))
    if abs(summe) > ctx.bagatelle:
        return [_b(ctx, "SB-06", "mittel",
            f"Saldenvortragskonten weisen per Saldo {eur(summe)} EUR aus "
            "(erwartet: 0,00).",
            "EB-Werte-Übernahme auf Vollständigkeit prüfen (fehlende "
            "Vortragsbuchungen).", betrag=summe)]
    return []


def sb_07_kassenbestand(ctx: Kontext) -> list[Befund]:
    grenze = Decimal(str(ctx.param["kasse_max_bestand"]))
    out = []
    for k in ctx.konten_in("kasse"):
        kum, spitze, spitze_datum = Decimal(0), Decimal(0), None
        for datum, _z, wert, _b_ in ctx.bewegungen[k]:
            kum += wert
            if kum > spitze:
                spitze, spitze_datum = kum, datum
        if spitze > grenze:
            out.append(_b(ctx, "SB-07", "hinweis",
                f"Kassenkonto {ctx.kontotext(k)}: Höchststand {eur(spitze)} EUR"
                f"{f' am {spitze_datum:%d.%m.%Y}' if spitze_datum else ''} "
                f"(Schwelle {eur(grenze)} EUR).",
                "Plausibilität des Kassenbestands (Bareinnahmenstruktur, "
                "Einzahlungsrhythmus) würdigen.",
                konto=k, datum=spitze_datum, betrag=spitze))
    return out


def sb_08_kassenluecken(ctx: Kontext) -> list[Befund]:
    grenze = int(ctx.param["kasse_luecke_tage"])
    out = []
    for k in ctx.konten_in("kasse"):
        daten = sorted({d for d, _z, _w, b in ctx.bewegungen[k]
                        if d and not ctx.ist_eb(b)})
        if len(daten) < 10:
            continue
        max_luecke, von, bis = 0, None, None
        for a, b_ in zip(daten, daten[1:]):
            delta = (b_ - a).days
            if delta > max_luecke:
                max_luecke, von, bis = delta, a, b_
        if max_luecke > grenze:
            out.append(_b(ctx, "SB-08", "hinweis",
                f"Kassenkonto {ctx.kontotext(k)}: {max_luecke} Tage ohne "
                f"Kassenbewegung ({von:%d.%m.%Y}–{bis:%d.%m.%Y}).",
                "Bei laufendem Bargeschäft Vollständigkeit der Kassen"
                "aufzeichnungen prüfen (Einzelaufzeichnungspflicht).",
                konto=k, datum=von))
    return out


# ---------------------------------------------------------------- AfA

def _av_zugaenge(ctx: Kontext) -> dict[int, Decimal]:
    zug: dict[int, Decimal] = defaultdict(Decimal)
    for gruppe in ("av_abnutzbar", "gwg"):
        for k in ctx.konten_in(gruppe):
            for _d, _z, wert, b in ctx.bewegungen[k]:
                if wert > 0 and not ctx.ist_eb(b) \
                        and not ctx.plan.in_gruppe(b.konto, "afa") \
                        and not ctx.plan.in_gruppe(b.gegenkonto, "afa"):
                    zug[k] += wert
    return zug


def af_01_zugang_ohne_afa(ctx: Kontext) -> list[Befund]:
    zug = _av_zugaenge(ctx)
    afa = sum((ctx.soll[k] for k in ctx.konten_in("afa")), Decimal(0))
    if zug and afa == 0:
        top = sorted(zug.items(), key=lambda e: -e[1])[:3]
        konten = ", ".join(f"{ctx.kontotext(k)}: {eur(v)} EUR" for k, v in top)
        return [_b(ctx, "AF-01", "hoch",
            f"Anlagenzugänge von {eur(sum(zug.values()))} EUR, aber keinerlei "
            f"AfA-Buchungen im Zeitraum (größte Zugänge: {konten}).",
            "Jahres-AfA berechnen und buchen (§ 7 EStG); Anlagenspiegel "
            "abstimmen.", betrag=sum(zug.values()))]
    return []


def af_02_afa_ohne_av(ctx: Kontext) -> list[Befund]:
    afa = sum((ctx.soll[k] for k in ctx.konten_in("afa")), Decimal(0))
    bestand = sum((ctx.saldo[k] for g in ("av_abnutzbar", "gwg")
                   for k in ctx.konten_in(g)), Decimal(0))
    if afa > 0 and bestand <= 0 and not _av_zugaenge(ctx):
        vorbehalt = ("" if ctx.eb_vorhanden else
                     " (Hinweis: Stapel enthält keine EB-Werte, Bestand ggf. "
                     "unvollständig)")
        return [_b(ctx, "AF-02", "mittel",
            f"AfA von {eur(afa)} EUR gebucht, aber kein abnutzbares "
            f"Anlagevermögen im Bestand erkennbar{vorbehalt}.",
            "Anlagenspiegel und Bezugsobjekte der AfA prüfen.", betrag=afa)]
    return []


def af_03_afa_grund_boden(ctx: Kontext) -> list[Befund]:
    out = []
    for b in ctx.buchungen:
        seiten = {b.konto, b.gegenkonto}
        if any(ctx.plan.in_gruppe(k, "afa") for k in seiten) \
                and any(ctx.plan.in_gruppe(k, "grund_boden") for k in seiten):
            out.append(_b(ctx, "AF-03", "hoch",
                f"AfA-Buchung gegen nicht abnutzbares Anlagevermögen "
                f"(Konto {b.konto} an {b.gegenkonto}).",
                "Grund und Boden ist nicht planmäßig abschreibbar; Buchung "
                "stornieren bzw. Gebäudeanteil abgrenzen.",
                konto=b.gegenkonto, datum=b.belegdatum, betrag=b.umsatz,
                beleg=b.belegfeld1, buchungstext=b.buchungstext, quelle=_q(b)))
    return out


def af_04_gwg_grenzen(ctx: Kontext) -> list[Befund]:
    grenze = Decimal(str(ctx.param["gwg_grenze_netto"]))
    ab = Decimal(str(ctx.param["gwg_wahlrecht_ab_eur"]))
    out, hinweise = [], 0
    for k in ctx.konten_in("gwg"):
        for _d, _z, wert, b in ctx.bewegungen[k]:
            if wert <= 0 or ctx.ist_eb(b):
                continue
            netto = ctx.plan.netto(b)
            if netto > grenze:
                out.append(_b(ctx, "AF-04", "mittel",
                    f"Zugang auf GWG-Konto {ctx.kontotext(k)} mit netto "
                    f"{eur(netto)} EUR über der GWG-Grenze ({eur(grenze)} EUR).",
                    "Umgliederung ins reguläre Anlagevermögen bzw. Sammelposten "
                    "(§ 6 Abs. 2, 2a EStG) prüfen.",
                    konto=k, datum=b.belegdatum, betrag=netto,
                    beleg=b.belegfeld1, buchungstext=b.buchungstext, quelle=_q(b)))
    for k in ctx.konten_in("av_abnutzbar"):
        if ctx.plan.in_gruppe(k, "gwg"):
            continue
        for _d, _z, wert, b in ctx.bewegungen[k]:
            if wert <= 0 or ctx.ist_eb(b) or hinweise >= 10:
                continue
            if ctx.plan.in_gruppe(b.konto, "afa") or ctx.plan.in_gruppe(b.gegenkonto, "afa"):
                continue
            netto = ctx.plan.netto(b)
            if ab <= netto <= grenze:
                hinweise += 1
                out.append(_b(ctx, "AF-04", "hinweis",
                    f"Anlagenzugang {ctx.kontotext(k)} netto {eur(netto)} EUR "
                    f"liegt unter der GWG-Grenze.",
                    "GWG-Sofortabschreibung bzw. Sammelposten als Wahlrecht "
                    "prüfen.", konto=k, datum=b.belegdatum, betrag=netto,
                    beleg=b.belegfeld1, buchungstext=b.buchungstext, quelle=_q(b)))
    return out


def af_05_aktivierung(ctx: Kontext) -> list[Befund]:
    ab = Decimal(str(ctx.param["aktivierung_ab_eur"]))
    out = []
    for k in ctx.konten_in("instandhaltung"):
        for _d, _z, wert, b in ctx.bewegungen[k]:
            if wert <= 0 or ctx.ist_eb(b):
                continue
            netto = ctx.plan.netto(b)
            if netto >= ab:
                out.append(_b(ctx, "AF-05", "mittel",
                    f"Einzelbuchung {eur(netto)} EUR netto auf Instandhaltungs"
                    f"konto {ctx.kontotext(k)}.",
                    "Aktivierungspflicht prüfen: Herstellungskosten, "
                    "wesentliche Verbesserung, anschaffungsnaher Aufwand "
                    "(§ 6 Abs. 1 Nr. 1a EStG).",
                    konto=k, datum=b.belegdatum, betrag=netto,
                    beleg=b.belegfeld1, buchungstext=b.buchungstext,
                    quelle=_q(b), llm=True))
    return out


# ---------------------------------------------------------------- USt/VSt

def us_01_vst_untypisch(ctx: Kontext) -> list[Befund]:
    out = []
    for b in ctx.buchungen:
        if not b.bu:
            continue
        st = ctx.plan.steuer(b)
        if not st or st[0] != "VSt" or st[2] is None:
            continue
        konto = b.konto if st[2] == "konto" else b.gegenkonto
        if ctx.plan.in_gruppe(konto, "vst_unueblich"):
            out.append(_b(ctx, "US-01", "mittel",
                f"Vorsteuerschlüssel {b.bu} auf Konto {ctx.kontotext(konto)} "
                f"(typischerweise nicht vorsteuerbehaftet).",
                "Vorsteuerabzug prüfen (§ 15 UStG); ggf. Schlüssel korrigieren "
                "und UStVA berichtigen.",
                konto=konto, datum=b.belegdatum, betrag=b.umsatz,
                beleg=b.belegfeld1, buchungstext=b.buchungstext, quelle=_q(b)))
    return out


def us_02_direkt_steuerkonten(ctx: Kontext) -> list[Befund]:
    out = []
    for gruppe in ("steuer_vst", "steuer_ust"):
        for k in ctx.konten_in(gruppe):
            bew = ctx.bewegungen[k]
            summe = sum((abs(w) for _d, _z, w, _b_ in bew), Decimal(0))
            out.append(_b(ctx, "US-02", "hinweis",
                f"{len(bew)} Direktbuchung(en) auf Steuerkonto "
                f"{ctx.kontotext(k)} (Summe {eur(summe)} EUR); automatische "
                f"Steuer läuft nicht über Stapelzeilen.",
                "Manuelle Steuerbuchungen (Korrekturen, Umbuchungen) auf "
                "Berechtigung prüfen.", konto=k, betrag=summe))
    return out


def us_03_schluessel(ctx: Kontext) -> list[Befund]:
    out = []
    unbekannt: Counter = Counter()
    historisch: dict[str, tuple[int, Decimal]] = {}
    jahr = ctx.datum_von.year if ctx.datum_von else 9999
    for b in ctx.buchungen:
        if not b.bu:
            continue
        ziffer = b.bu[-1]
        if ziffer != "0" and ziffer not in ctx.plan.steuerschluessel:
            unbekannt[b.bu] += 1
            continue
        st = ctx.plan.steuer(b)
        if st and st[1] == 16 and jahr >= 2021:
            anz, summe = historisch.get(b.bu, (0, Decimal(0)))
            historisch[b.bu] = (anz + 1, summe + b.umsatz)
    for schluessel, anz in unbekannt.items():
        out.append(_b(ctx, "US-03", "hinweis",
            f"BU-Schlüssel '{schluessel}' ist in der Konfiguration nicht "
            f"hinterlegt ({anz} Buchung(en)).",
            "Schlüssel fachlich klären; ggf. konten_config.json ergänzen."))
    for schluessel, (anz, summe) in historisch.items():
        out.append(_b(ctx, "US-03", "mittel",
            f"Historischer 16%-Schlüssel '{schluessel}' im Prüfjahr {jahr} "
            f"verwendet ({anz} Buchung(en), Summe {eur(summe)} EUR).",
            "Steuersatz prüfen (16 % galt nur 07–12/2020); Rechnungen und "
            "UStVA korrigieren.", betrag=summe))
    return out


def us_04_bewirtung(ctx: Kontext) -> list[Befund]:
    bewirtung = sum((ctx.soll[k] for k in ctx.konten_in("bewirtung")), Decimal(0))
    nabz = sum((abs(ctx.saldo[k]) + ctx.soll[k] for k in ctx.konten_in("bewirtung_nabz")), Decimal(0))
    if bewirtung > 0 and nabz == 0:
        return [_b(ctx, "US-04", "mittel",
            f"Bewirtungsaufwand {eur(bewirtung)} EUR gebucht, aber kein nicht "
            "abziehbarer Anteil (30 %) erkennbar.",
            "Aufteilung nach § 4 Abs. 5 Nr. 2 EStG prüfen; Bewirtungsbelege "
            "auf Vollständigkeit der Angaben kontrollieren.", betrag=bewirtung)]
    return []


def us_05_schluessel_abweichler(ctx: Kontext) -> list[Befund]:
    min_n = int(ctx.param["schluessel_min_n"])
    dominanz = float(ctx.param["schluessel_dominanz"])
    profile: dict[int, Counter] = defaultdict(Counter)
    beispiele: dict[tuple[int, str], list] = defaultdict(list)
    for b in ctx.buchungen:
        if ctx.ist_eb(b):
            continue
        seite = None
        if ctx.plan.ist_guv(b.konto):
            seite = b.konto
        elif ctx.plan.ist_guv(b.gegenkonto):
            seite = b.gegenkonto
        if seite is None:
            continue
        st = ctx.plan.steuer(b)
        signatur = f"{st[0]} {st[1]} %" if st else "ohne Steuerschlüssel"
        profile[seite][signatur] += 1
        if len(beispiele[(seite, signatur)]) < 3:
            beispiele[(seite, signatur)].append(b)
    out = []
    for konto, zaehler in sorted(profile.items()):
        n = sum(zaehler.values())
        if n < min_n:
            continue
        (top_sig, top_n), = zaehler.most_common(1)
        if top_n / n >= dominanz and top_n < n:
            abweichler = [(sig, anz) for sig, anz in zaehler.items() if sig != top_sig]
            details = []
            for sig, anz in abweichler:
                for b in beispiele[(konto, sig)]:
                    datum = f"{b.belegdatum:%d.%m.%Y}" if b.belegdatum else "?"
                    details.append(f"{datum} {eur(b.umsatz)} EUR [{sig}]")
            out.append(_b(ctx, "US-05", "hinweis",
                f"Konto {ctx.kontotext(konto)}: {top_n}/{n} Buchungen mit "
                f"'{top_sig}', Abweichler: {'; '.join(details[:5])}.",
                "Abweichende Steuerschlüssel auf Richtigkeit prüfen "
                "(vergessener bzw. falscher Schlüssel).", konto=konto))
    return out


def us_06_07_verprobung(ctx: Kontext) -> list[Befund]:
    ust = vst = Decimal(0)
    for b in ctx.buchungen:
        st = ctx.plan.steuer(b)
        if not st or not st[1] or st[2] is None:
            continue
        s = b.umsatz if b.sh == "S" else -b.umsatz
        if b.storno:
            s = -s
        wert_seite = s if st[2] == "konto" else -s
        anteil = (wert_seite * st[1] / (100 + st[1])).quantize(Decimal("0.01"))
        if st[0] == "USt":
            ust -= anteil   # USt entsteht bei Haben auf der Erlösseite
        elif st[0] == "VSt":
            vst += anteil   # VSt entsteht bei Soll auf der Aufwandsseite
    ctx.kennzahlen["USt rechnerisch (aus Schlüsseln/Automatik)"] = f"{eur(ust)} EUR"
    ctx.kennzahlen["VSt rechnerisch (aus Schlüsseln/Automatik)"] = f"{eur(vst)} EUR"
    if ctx.susa is None:
        ctx.skip("US-06", "Verprobung erfordert SuSa (--susa)")
        ctx.skip("US-07", "Verprobung erfordert SuSa (--susa)")
        return []
    toleranz = Decimal(str(ctx.param["verprobung_toleranz_eur"]))
    out = []
    ist_ust = -sum((s for k, s in ctx.susa.items()
                    if ctx.plan.in_gruppe(k, "steuer_ust")), Decimal(0))
    ist_vst = sum((s for k, s in ctx.susa.items()
                   if ctx.plan.in_gruppe(k, "steuer_vst")), Decimal(0))
    for cid, name, soll, ist in (("US-06", "USt", ust, ist_ust),
                                 ("US-07", "VSt", vst, ist_vst)):
        diff = ist - soll
        if abs(diff) > toleranz:
            out.append(_b(ctx, cid, "hinweis",
                f"{name}-Verprobung: rechnerisch {eur(soll)} EUR, laut SuSa "
                f"{eur(ist)} EUR (Differenz {eur(diff)} EUR).",
                "Differenz aufklären; UStVA-/Zahllast-Umbuchungen und "
                "Automatikkonten-Zuordnung (konten_config.json) berücksichtigen.",
                betrag=diff))
    return out


# ------------------------------------------------- Ausgangsrechnungen

_RE_MUSTER = re.compile(r"^(.*?)(\d+)\s*$")


def _rechnungen(ctx: Kontext):
    """Ausgangsrechnungen = Buchungen Debitor(-Sammelkonto) gegen Erlöskonto.
    Liefert je (Prefix, Nummer) die aggregierten Vorgänge."""
    roh = []
    gesamt = 0
    for b in ctx.buchungen:
        ertragsseite = lambda k: (ctx.plan.in_gruppe(k, "ertrag")
                                  or ctx.plan.in_gruppe(k, "erloesschmaelerung"))
        if ctx.plan.ist_debitorisch(b.konto) and ertragsseite(b.gegenkonto):
            deb = b.konto
        elif ctx.plan.ist_debitorisch(b.gegenkonto) and ertragsseite(b.konto):
            deb = b.gegenkonto
        else:
            continue
        gesamt += 1
        m = _RE_MUSTER.match(b.belegfeld1.strip())
        if m and len(m.group(2)) >= 2:
            roh.append((m.group(1).strip(), int(m.group(2)), deb, b))
    return roh, gesamt


def re_checks(ctx: Kontext) -> list[Befund]:
    min_anzahl = int(ctx.param["re_min_anzahl"])
    roh, gesamt = _rechnungen(ctx)
    if gesamt < min_anzahl:
        grund = f"zu wenige Ausgangsrechnungen erkannt ({gesamt} < {min_anzahl})"
        for cid in ("RE-01", "RE-02", "RE-03"):
            ctx.skip(cid, grund)
        return []
    if len(roh) / gesamt < 0.6:
        grund = ("Belegfeld 1 überwiegend nicht als Rechnungsnummer "
                 f"interpretierbar ({len(roh)}/{gesamt})")
        for cid in ("RE-01", "RE-02", "RE-03"):
            ctx.skip(cid, grund)
        return []
    out = []
    prefixe: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for prefix, nr, deb, b in roh:
        prefixe[prefix][nr].append((deb, b))
    for prefix, nummern in sorted(prefixe.items()):
        if sum(len(v) for v in nummern.values()) < min_anzahl:
            continue
        anzeige = prefix or "(ohne Präfix)"
        # RE-02: eine Nummer, mehrere Vorgänge (verschiedenes Datum/Debitor)
        rechnung_je_nr: dict[int, tuple] = {}
        for nr, eintraege in nummern.items():
            kombis = {(b.belegdatum, deb) for deb, b in eintraege}
            if len(kombis) > 1:
                details = "; ".join(
                    f"{deb} am {(b.belegdatum and f'{b.belegdatum:%d.%m.%Y}') or '?'} "
                    f"über {eur(b.umsatz)} EUR" for deb, b in eintraege[:4])
                out.append(_b(ctx, "RE-02", "hoch",
                    f"Rechnungsnummer {anzeige}{nr} mehrfach vergeben: {details}.",
                    "Doppelvergabe klären (§ 14 Abs. 4 Nr. 4 UStG: einmalige, "
                    "fortlaufende Nummer); ggf. Doppelerfassung stornieren.",
                    konto=eintraege[0][0], datum=eintraege[0][1].belegdatum,
                    betrag=sum((b.umsatz for _d, b in eintraege), Decimal(0)),
                    beleg=eintraege[0][1].belegfeld1,
                    quelle=_q(eintraege[0][1])))
            rechnung_je_nr[nr] = (min((b.belegdatum for _d, b in eintraege
                                       if b.belegdatum), default=None),
                                  eintraege[0][1])
        # RE-01: Lücken in der Folge
        nrs = sorted(nummern)
        fehlend = [n for n in range(nrs[0], nrs[-1] + 1) if n not in nummern]
        if fehlend:
            if (nrs[-1] - nrs[0] + 1) > 10 * len(nrs):
                out.append(_b(ctx, "RE-01", "hinweis",
                    f"Nummernkreis '{anzeige}' sehr dünn besetzt "
                    f"({len(nrs)} Nummern zwischen {nrs[0]} und {nrs[-1]}); "
                    "vermutlich Mischformat oder Teilexport.",
                    "Nummernsystematik klären, dann erneut prüfen."))
            else:
                max_liste = int(ctx.param["re_luecken_max_liste"])
                out.append(_b(ctx, "RE-01", "mittel",
                    f"Nummernkreis '{anzeige}' ({nrs[0]}–{nrs[-1]}): "
                    f"{len(fehlend)} fehlende Nummer(n): "
                    f"{_verdichte(fehlend, max_liste)}.",
                    "Fehlende Nummern aufklären: Storno, verlorene Rechnung, "
                    "nicht erfasster Umsatz oder Teilexport (GoBD-Vollständigkeit).",
                    betrag=None))
        # RE-03: Datum läuft der Nummernfolge entgegen
        toleranz = timedelta(days=int(ctx.param["re_datum_toleranz_tage"]))
        verstoesse = []
        letzte = None
        for nr in nrs:
            datum, b = rechnung_je_nr[nr]
            if datum is None:
                continue
            if letzte and datum < letzte[1] - toleranz:
                verstoesse.append(f"Nr. {nr} ({datum:%d.%m.%Y}) vor "
                                  f"Nr. {letzte[0]} ({letzte[1]:%d.%m.%Y})")
            if letzte is None or datum > letzte[1]:
                letzte = (nr, datum)
        if verstoesse:
            out.append(_b(ctx, "RE-03", "hinweis",
                f"Nummernkreis '{anzeige}': Belegdatum läuft der Nummernfolge "
                f"entgegen: {'; '.join(verstoesse[:10])}.",
                "Rückdatierung bzw. nachträgliche Rechnungserstellung klären."))
    return out


def _verdichte(zahlen: list[int], maximal: int) -> str:
    bereiche, start, ende = [], zahlen[0], zahlen[0]
    for z in zahlen[1:]:
        if z == ende + 1:
            ende = z
        else:
            bereiche.append((start, ende))
            start = ende = z
    bereiche.append((start, ende))
    texte = [f"{a}" if a == b else f"{a}–{b}" for a, b in bereiche]
    if len(texte) > maximal:
        return ", ".join(texte[:maximal]) + f" … ({len(texte) - maximal} weitere Bereiche)"
    return ", ".join(texte)


# ---------------------------------------------------------------- OPOS

def op_01_02_personensalden(ctx: Kontext) -> list[Befund]:
    out = []
    for cid, pruef, vorzeichen, art in (
            ("OP-01", ctx.plan.ist_debitor, -1, "Debitor"),
            ("OP-02", ctx.plan.ist_kreditor, 1, "Kreditor")):
        treffer = [(k, s) for k, s in ctx.saldo.items()
                   if pruef(k) and s * vorzeichen > ctx.bagatelle]
        treffer.sort(key=lambda e: -abs(e[1]))
        for k, s in treffer[:50]:
            seite = "Haben" if vorzeichen < 0 else "Soll"
            out.append(_b(ctx, cid, "mittel",
                f"{art} {ctx.kontotext(k)} mit {seite}-Saldo {eur(s)} EUR.",
                "Ursache klären: Doppelzahlung, fehlende Rechnung, erhaltene "
                "Anzahlung (ggf. umgliedern, § 246 HGB Saldierungsverbot).",
                konto=k, betrag=s))
        if len(treffer) > 50:
            out.append(_b(ctx, cid, "mittel",
                f"… {len(treffer) - 50} weitere {art}en mit untypischem Saldo."))
    return out


def op_03_alte_posten(ctx: Kontext) -> list[Befund]:
    if ctx.opos is None:
        ctx.skip("OP-03", "erfordert OPOS-Liste (--opos)")
        return []
    if ctx.datum_bis is None:
        ctx.skip("OP-03", "erfordert Stichtag (Header-Zeitraum)")
        return []
    grenze = ctx.datum_bis - timedelta(days=int(ctx.param["opos_alt_tage"]))
    kleinst = Decimal(str(ctx.param["opos_kleinst_eur"]))
    out, uebrig = [], 0
    limit = _limit(ctx)
    for p in ctx.opos:
        datum = p.faellig or p.belegdatum
        if datum and datum < grenze and p.betrag >= kleinst:
            if len(out) >= limit:
                uebrig += 1
                continue
            art = "Debitor" if ctx.plan.ist_debitor(p.konto) else "Kreditor"
            out.append(_b(ctx, "OP-03", "mittel",
                f"Offener Posten {art} {ctx.kontotext(p.konto)} über "
                f"{eur(p.betrag)} EUR, fällig/belegdatiert {datum:%d.%m.%Y} "
                f"(älter als {ctx.param['opos_alt_tage']} Tage).",
                "Werthaltigkeit prüfen (EWB/PWB bei Debitoren); bei Kreditoren "
                "Grund der Nichtzahlung klären.",
                konto=p.konto, datum=datum, betrag=p.betrag, beleg=p.beleg))
    _rest(ctx, out, "OP-03", uebrig, "überfällige Posten")
    return out


def op_04_direktverrechnung(ctx: Kontext) -> list[Befund]:
    out, uebrig = [], 0
    limit = _limit(ctx)
    for b in ctx.buchungen:
        paar = {b.konto, b.gegenkonto}
        if any(ctx.plan.ist_debitor(k) for k in paar) \
                and any(ctx.plan.ist_kreditor(k) for k in paar):
            if len(out) >= limit:
                uebrig += 1
                continue
            out.append(_b(ctx, "OP-04", "hinweis",
                f"Direktverrechnung Debitor/Kreditor ({b.konto} an "
                f"{b.gegenkonto}) über {eur(b.umsatz)} EUR.",
                "Aufrechnungslage dokumentieren (Saldierungsverbot § 246 "
                "Abs. 2 HGB beachten).",
                konto=b.konto, gegenkonto=b.gegenkonto, datum=b.belegdatum,
                betrag=b.umsatz, beleg=b.belegfeld1,
                buchungstext=b.buchungstext, quelle=_q(b)))
    _rest(ctx, out, "OP-04", uebrig, "Direktverrechnungen")
    return out


# ------------------------------------------------------ Personal/Privat

def pp_01_kfz_privat(ctx: Kontext) -> list[Befund]:
    kfz = sum((ctx.soll[k] for k in ctx.konten_in("kfz_aufwand")), Decimal(0))
    uwa = sum((ctx.anzahl[k] for k in ctx.konten_in("uwa_kfz")), 0)
    if kfz >= Decimal(str(ctx.param["kfz_privat_ab_eur"])) and uwa == 0:
        return [_b(ctx, "PP-01", "hinweis",
            f"Kfz-Kosten von {eur(kfz)} EUR, aber keine private Nutzungs"
            "entnahme (1 %-Regelung/Fahrtenbuch) erkennbar.",
            "Privatnutzung prüfen; entfällt bei reinen Pool-/Nutzfahrzeugen "
            "oder Versteuerung über Lohn.", betrag=kfz)]
    return []


def pp_02_privat_jahresende(ctx: Kontext) -> list[Befund]:
    if ctx.datum_bis is None:
        return []
    fenster = ctx.datum_bis - timedelta(days=int(ctx.param["wj_ende_fenster_tage"]))
    daten = [d for k in ctx.konten_in("privat")
             for d, _z, _w, b in ctx.bewegungen[k]
             if d and not ctx.ist_eb(b)]
    if len(daten) >= 3 and min(daten) > fenster:
        return [_b(ctx, "PP-02", "hinweis",
            f"Alle {len(daten)} Privatbuchungen liegen in den letzten "
            f"{ctx.param['wj_ende_fenster_tage']} Tagen des Zeitraums.",
            "Sammel-/Nachbuchung: unterjährige Entnahmen (Bar, Sachbezüge, "
            "uWA) auf Vollständigkeit prüfen.", datum=min(daten))]
    return []


def pp_03_lohn_ohne_verb(ctx: Kontext) -> list[Befund]:
    lohn = sum((ctx.soll[k] for k in ctx.konten_in("lohn")), Decimal(0))
    verb = sum((ctx.anzahl[k] for k in ctx.konten_in("lst_sv_verb")), 0)
    if lohn > 0 and verb == 0:
        return [_b(ctx, "PP-03", "mittel",
            f"Lohn-/Gehaltsaufwand {eur(lohn)} EUR ohne Buchungen auf "
            "LSt-/SV-Verbindlichkeitskonten.",
            "Lohnbuchungsschnittstelle prüfen: Verbindlichkeiten (LSt, SV) "
            "und Abgrenzung Dezember-Löhne kontrollieren.", betrag=lohn)]
    return []


ALLE_FACHLICH = [
    sb_01_negative_kasse, sb_02_saldenvorzeichen, sb_03_geldtransit,
    sb_04_interim, sb_05_susa_abgleich, sb_06_eb_differenz,
    sb_07_kassenbestand, sb_08_kassenluecken,
    af_01_zugang_ohne_afa, af_02_afa_ohne_av, af_03_afa_grund_boden,
    af_04_gwg_grenzen, af_05_aktivierung,
    us_01_vst_untypisch, us_02_direkt_steuerkonten, us_03_schluessel,
    us_04_bewirtung, us_05_schluessel_abweichler, us_06_07_verprobung,
    re_checks,
    op_01_02_personensalden, op_03_alte_posten, op_04_direktverrechnung,
    pp_01_kfz_privat, pp_02_privat_jahresende, pp_03_lohn_ohne_verb,
]
