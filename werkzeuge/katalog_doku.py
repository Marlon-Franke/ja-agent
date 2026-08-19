"""Generiert die aus soll_katalog.json, befunde.KATALOG, erwartung.json und
plugin.json abgeleiteten Doku-Bloecke und prueft die Konsistenz der
Katalog-Dokumentation (Revisionsbefunde P1.5, P2.1, P2.2).

  py werkzeuge/katalog_doku.py --write   Bloecke neu schreiben
  py werkzeuge/katalog_doku.py --check   nur pruefen (Exit 1 bei Drift)

Kanonische Quelle der Soll-Katalogpunkte ist werkzeuge/soll_katalog.json
(je Punkt: stabile Soll-ID Kxx.yy, Kapitel, Soll-Klasse, Umsetzungsstatus,
CHECK-IDs, Datenquellen, Abbildung auf die Checkbox-Zeilen des
Referenzkatalogs). Aenderungen an Katalogpunkten erfolgen NUR dort; die
Dokumente werden generiert.

Generierte Bloecke (Marker, Inhalt dazwischen wird ersetzt):
  README.md
    <!-- KATALOG:SOLL:START --> ... END       Pruefkatalog Kap. 1-20
                                              (Checkliste, ### n.)
  skills/ja-pruefung/references/pruefkatalog.md
    <!-- KATALOG:SOLL:START --> ... END       Abdeckungsmatrix Kap. 1-20
                                              (Tabellen mit Soll-ID, ## n.)
    <!-- KATALOG:EBENEN:START --> ... END     Ebenen-Tabelle (Ebene -> Checks)
    <!-- KATALOG:REGISTER:START --> ... END   Check-Register (ID, Name,
                                              Bereich, Ebene, Klasse,
                                              Soll-Punkte, Erwartungsbild)
  Pruefkatalog fuer einen Python-basierten Accounting-Agenten.md
    <!-- KATALOG:REFERENZSTAND:START --> ... END   Referenzversion = Plugin-
                                              Version (Revisionsbefund P2.1)

Konsistenzpruefung (pruefe(), Build-Gate in baue_dist.py / release_check.py):
  * generierte Bloecke aktuell;
  * soll_katalog.json strukturell gueltig (IDs eindeutig und kapitelgebunden,
    Status/Klasse aus dem erlaubten Vorrat, Statusregeln);
  * jede CHECK-ID eines Punkts existiert in befunde.KATALOG und wird im
    Umsetzungstext genannt; jeder KATALOG-Check deckt mindestens einen
    Soll-Punkt ab (kein verwaister Check);
  * KI-Kennzeichen und Datenquellen-Schluessel konsistent;
  * jede Checkbox-Zeile des Referenzkatalogs ist genau einem Soll-Punkt
    desselben Kapitels zugeordnet, die Soll-Klasse ist die Vereinigung der
    Referenzklassen (Punkte ohne Referenz = Ergaenzungen des Agenten);
  * keine CHECK-ID in README-Pruefkatalog/Matrix ausserhalb des KATALOGs.

Semantik (Klaerung der Klassifikationsdrift, Release-Readiness-Report
Befunde 5-9): Die [R]/[P]/[A]/[X]-Tags an den Katalogpunkten in README und
Matrix sind die Klasse des SOLL-Katalogpunkts (Referenzkatalog). Ebene und
Klasse des IMPLEMENTIERTEN Checks fuehrt allein befunde.KATALOG - sie
steuern Bericht und Excel/PBI-Ausweis. Beides darf abweichen (ein P-Check
kann einen R-Katalogpunkt abdecken); die implementierte Sicht wird deshalb
hier generiert statt von Hand gepflegt.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
MATRIX = BASIS / "skills" / "ja-pruefung" / "references" / "pruefkatalog.md"
README = BASIS / "README.md"
REFERENZ = BASIS / "Prüfkatalog für einen Python-basierten Accounting-Agenten.md"
SOLL = BASIS / "werkzeuge" / "soll_katalog.json"
ERWARTUNG = BASIS / "testdaten" / "erwartung.json"
PLUGIN_MANIFEST = BASIS / ".claude-plugin" / "plugin.json"
EBENEN_FRAGE = {
    1: ("1 – technische Integrität", "Daten vollständig und konsistent?"),
    2: ("2 – Regelprüfung",
        "Verstoß gegen eindeutige Buchungs-/Bilanz-/Steuerregel?"),
    3: ("3 – Plausibilität",
        "Passt der Sachverhalt zu Schwellen, Struktur, Relationen?"),
    4: ("4 – Anomalie",
        "Statistisch/strukturell ungewöhnlich ohne konkreten Regelverstoß?"),
}
KLASSEN = {"R": "Rule-based", "P": "Plausibilität", "A": "Anomalie"}
# CHECK-IDs im Fliesstext, auch verkuerzt: "OP-03/05/06" -> OP-03, OP-05, OP-06
ID_MUSTER = re.compile(r"\b([A-Z]{2})-(\d{2}(?:/\d{2})*)\b")
KI_MUSTER = re.compile(r"\bKI\b")  # KI-Beteiligung (auch "KI-Beurteilung")
KI_FETT_MUSTER = re.compile(r"\bKI\b(?![-\w])")  # nur alleinstehendes "KI" -> **KI**
KAPITEL = range(1, 21)  # Katalogkapitel 1-20 in README und Matrix
PUNKT_KAPITEL = range(1, 18)  # Kapitel mit Soll-Punkten (18/19 Prosa, 20 Quellen)
SOLL_ID = re.compile(r"^K(\d{2})\.(\d{2})$")
STATUS = ("check", "ki", "bericht", "strukturell", "offen", "zusatz")
UMGESETZT = ("check", "ki", "bericht", "strukturell")  # README [x] / Matrix ✔
KLASSE_REIHE = "RPAX"
PLUS = "➕"
LAEUFE = ("standard", "dq02", "co02")
LAEUFE_TITEL = "Standard · DQ-02-Lauf · CO-02-Lauf"


def _katalog():
    sys.path.insert(0, str(BASIS / "werkzeuge"))
    try:
        import befunde  # noqa: PLC0415
    finally:
        sys.path.pop(0)
    return befunde.KATALOG


def lade_soll(pfad: Path = SOLL) -> dict:
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    for feld in ("kapitel", "datenquellen", "punkte"):
        if not isinstance(daten.get(feld), list):
            raise ValueError(f"{pfad.name}: Liste '{feld}' fehlt")
    return daten


def _kompakt(ids: list[str], alle_ids: set[str]) -> str:
    """'DV-01, DV-02, DQ-01' -> 'DV, DQ-01' (Praefix allein, wenn vollstaendig)."""
    je_praefix: dict[str, list[str]] = defaultdict(list)
    for cid in ids:
        je_praefix[cid.split("-")[0]].append(cid.split("-")[1])
    teile = []
    for praefix, nummern in je_praefix.items():
        gesamt = {c.split("-")[1] for c in alle_ids if c.startswith(praefix + "-")}
        if set(nummern) == gesamt:
            teile.append(praefix)
        else:
            teile.append(f"{praefix}-" + "/".join(sorted(nummern)))
    return ", ".join(teile)


def ebenen_tabelle(katalog) -> str:
    alle = {cid for cid, *_ in katalog}
    je_ebene: dict[int, list[str]] = defaultdict(list)
    for cid, _n, _b, ebene, _k in katalog:
        je_ebene[ebene].append(cid)
    zeilen = ["| Ebene | Frage | Checks (Präfixe) |", "|---|---|---|"]
    for ebene in sorted(EBENEN_FRAGE):
        titel, frage = EBENEN_FRAGE[ebene]
        zeilen.append(f"| {titel} | {frage} | "
                      f"{_kompakt(je_ebene.get(ebene, []), alle)} |")
    return "\n".join(zeilen)


# --- Erwartungsbild je Check (Evidenz: testdaten/erwartung.json) -------------

def _erwartung_je_check() -> dict[str, str]:
    """CHECK-ID -> 'Standard · DQ-02 · CO-02'-Kurzform aus erwartung.json;
    '=' = vom Basislauf geerbt, 'Skip' = begruendet uebersprungen, '0' =
    Nullbefund (geprueft, ohne Befund)."""
    sys.path.insert(0, str(BASIS / "werkzeuge"))
    try:
        import pruefe_erwartung  # noqa: PLC0415
    finally:
        sys.path.pop(0)
    erwartung = pruefe_erwartung.lade_erwartung(ERWARTUNG)
    effektiv = {name: pruefe_erwartung.effektiver_lauf(erwartung, name)["checks"]
                for name in LAEUFE}
    eigene = {name: set(erwartung["laeufe"][name].get("checks", {})) for name in LAEUFE}

    def kurz(eintrag: dict) -> str:
        if eintrag.get("status") == "skip":
            return "Skip"
        treffer = eintrag.get("treffer") or {}
        teile = [f"{treffer[s]} {s}" for s in ("hoch", "mittel", "hinweis") if treffer.get(s)]
        return ", ".join(teile) if teile else "0"

    ergebnis: dict[str, str] = {}
    alle_ids = set().union(*effektiv.values())
    for cid in alle_ids:
        spalten = []
        for name in LAEUFE:
            eintrag = effektiv[name].get(cid)
            if eintrag is None:
                spalten.append("–")
            elif name != LAEUFE[0] and cid not in eigene[name]:
                spalten.append("=")
            else:
                spalten.append(kurz(eintrag))
        ergebnis[cid] = " · ".join(spalten)
    return ergebnis


def register_tabelle(katalog, soll: dict | None = None) -> str:
    soll = soll or lade_soll()
    punkte_je_check: dict[str, list[str]] = defaultdict(list)
    for punkt in soll["punkte"]:
        for cid in punkt["checks"]:
            punkte_je_check[cid].append(punkt["id"])
    erwartung = _erwartung_je_check()
    zeilen = [f"| ID | Check | Bereich | Ebene | Klasse | Soll-Punkte | "
              f"Erwartungsbild ({LAEUFE_TITEL}) |",
              "|---|---|---|---|---|---|---|"]
    for cid, name, bereich, ebene, klasse in katalog:
        basis, *zusatz = klasse.split("/")
        klasse_txt = f"{basis} ({KLASSEN[basis]})" + (" +X Zusatzdaten" if zusatz else "")
        zeilen.append(f"| {cid} | {name} | {bereich} | {ebene} | {klasse_txt} | "
                      f"{', '.join(punkte_je_check.get(cid, [])) or '–'} | "
                      f"{erwartung.get(cid, '–')} |")
    zeilen.append("")
    zeilen.append(f"{len(katalog)} Checks (= `len(befunde.KATALOG)`). Soll-Punkte = "
                  f"Soll-IDs aus `werkzeuge/soll_katalog.json`, die der Check abdeckt; "
                  f"Erwartungsbild = Treffer je Schwere in den drei Referenzläufen aus "
                  f"`testdaten/erwartung.json` („=“ wie Standardlauf, „Skip“ begründet "
                  f"übersprungen, „0“ Nullbefund = geprüft, ohne Befund).")
    return "\n".join(zeilen)


def plugin_version() -> str:
    daten = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    version = daten.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(".claude-plugin/plugin.json: 'version' fehlt")
    return version


def referenzstand_block(version: str) -> str:
    return (f"**Referenzstand:** Version **v{version}** des JA-Agenten "
            f"(= `version` in `.claude-plugin/plugin.json`, Repository-Tag "
            f"`v{version}` mit dem zugehörigen Commit; dieser Block wird von "
            f"`werkzeuge/katalog_doku.py` generiert und im Build geprüft).")


# --- Soll-Katalog rendern (README-Checkliste / Abdeckungsmatrix) -------------

def _md_ids(text: str) -> str:
    """CHECK-IDs in Backticks, 'KI' fett (README-Schreibweise)."""
    text = ID_MUSTER.sub(lambda m: f"`{m.group(0)}`", text)
    return KI_FETT_MUSTER.sub("**KI**", text)  # "KI-Kandidat" bleibt unveraendert


def _zelle(text: str) -> str:
    return text.replace("|", "\\|")


def _kapitel_map(soll: dict) -> dict[int, dict]:
    return {k["nr"]: k for k in soll["kapitel"]}


def _punkte_je_kapitel(soll: dict) -> dict[int, list[dict]]:
    je: dict[int, list[dict]] = defaultdict(list)
    for punkt in soll["punkte"]:
        je[punkt["kapitel"]].append(punkt)
    return je


def _readme_zeile(punkt: dict) -> str:
    tag = f"[{punkt['klasse']}] " if punkt.get("klasse") else ""
    status = punkt["status"]
    zusatz = punkt.get("zusatz")
    if status == "zusatz":
        return f"- [ ] {tag}{punkt['punkt']} {_md_ids(zusatz)}"
    if status == "offen":
        rest = f"; {_md_ids(zusatz)}" if zusatz else ""
        return f"- [ ] {tag}{punkt['punkt']} – Ausbaustufe: {_md_ids(punkt['umsetzung'])}{rest}"
    rest = f"; {_md_ids(zusatz)}" if zusatz else ""
    return f"- [x] {tag}{punkt['punkt']} → {_md_ids(punkt['umsetzung'])}{rest}"


def _matrix_status(punkt: dict) -> str:
    status = punkt["status"]
    zusatz = punkt.get("zusatz")
    if status == "zusatz":
        return zusatz
    if status == "offen":
        text = f"Ausbaustufe: {punkt['umsetzung']}"
    elif status in ("check", "bericht"):
        text = f"✔ {punkt['umsetzung']}"
    else:  # ki, strukturell
        text = punkt["umsetzung"]
    if punkt.get("detail"):
        text += f" – {punkt['detail']}"
    if zusatz:
        text += f"; {zusatz}"
    return text


def _quellen_tabelle(soll: dict, mit_punkten: bool) -> list[str]:
    je_quelle: dict[str, list[str]] = defaultdict(list)
    for punkt in soll["punkte"]:
        for key in punkt["quellen"]:
            je_quelle[key].append(punkt)
    kopf = "| # | Quelle | Status |" + (" Katalogpunkte |" if mit_punkten else "")
    zeilen = [kopf, "|---|---|---|" + ("---|" if mit_punkten else "")]
    for quelle in soll["datenquellen"]:
        zeile = f"| {quelle['nr']} | {_zelle(quelle['name'])} | {_zelle(quelle['status'])} |"
        if mit_punkten:
            punkte = je_quelle.get(quelle["key"], [])
            if quelle["key"] == "stapel":
                text = "alle (Pflichtquelle)"
            else:
                umgesetzt = [p["id"] for p in punkte if p["status"] in UMGESETZT]
                offen = [p["id"] for p in punkte if p["status"] not in UMGESETZT]
                teile = []
                if umgesetzt:
                    teile.append(", ".join(umgesetzt))
                if offen:
                    teile.append(f"{PLUS} " + ", ".join(offen))
                text = " · ".join(teile) or "–"
            zeile += f" {text} |"
        zeilen.append(zeile)
    if mit_punkten:
        zeilen += ["", f"Katalogpunkte: Soll-IDs, die die Quelle nutzen oder für ihren "
                   f"{PLUS}-Zusatz benötigen; {PLUS} = offene Punkte (zusätzliche "
                   "Prüfung/Ausbaustufe), die auf diese Quelle warten."]
    return zeilen


def soll_block(soll: dict, ueberschrift: str, matrix: bool) -> str:
    """Kapitel 1-20 als Markdown: README-Checkliste (matrix=False) bzw.
    Abdeckungsmatrix-Tabellen (matrix=True). `ueberschrift` = '### ' / '## '."""
    kapitel = _kapitel_map(soll)
    je_kapitel = _punkte_je_kapitel(soll)
    teile: list[str] = []
    for nr in KAPITEL:
        kap = kapitel[nr]
        block = [f"{ueberschrift}{nr}. {kap['titel']}", ""]
        if kap.get("hinweis"):
            block += [kap["hinweis"], ""]
        if kap.get("prosa"):
            block += list(kap["prosa"])
        elif nr == 20:
            block += _quellen_tabelle(soll, mit_punkten=matrix)
        elif matrix:
            spalte = kap.get("spalte", "Katalogpunkt")
            block += [f"| ID | {spalte} | Klasse | Umsetzung |", "|---|---|---|---|"]
            for punkt in je_kapitel.get(nr, []):
                block.append(f"| {punkt['id']} | {_zelle(punkt['punkt'])} | "
                             f"{punkt.get('klasse') or '–'} | "
                             f"{_zelle(_matrix_status(punkt))} |")
        else:
            gruppe = None
            for punkt in je_kapitel.get(nr, []):
                if punkt.get("gruppe") != gruppe:
                    gruppe = punkt.get("gruppe")
                    if gruppe:
                        block += ["", f"**{gruppe}**", ""]
                block.append(_readme_zeile(punkt))
        teile.append("\n".join(block))
    return "\n\n".join(teile)


def _ersetze(text: str, name: str, inhalt: str, datei: Path) -> str:
    # Block darf leer sein (frisch gesetzte Marker); Ersetzung ist idempotent.
    muster = re.compile(rf"(<!-- KATALOG:{name}:START -->\n).*?(<!-- KATALOG:{name}:END -->)",
                        re.S)
    if not muster.search(text):
        raise ValueError(f"Marker KATALOG:{name}:START/END fehlt in {datei.name}")
    return muster.sub(lambda m: m.group(1) + inhalt + "\n" + m.group(2), text, count=1)


def erzeuge_matrix(text: str) -> str:
    katalog = _katalog()
    soll = lade_soll()
    bloecke = {"SOLL": soll_block(soll, "## ", matrix=True),
               "EBENEN": ebenen_tabelle(katalog),
               "REGISTER": register_tabelle(katalog, soll)}
    for name, inhalt in bloecke.items():
        text = _ersetze(text, name, inhalt, MATRIX)
    return text


def erzeuge_readme(text: str) -> str:
    return _ersetze(text, "SOLL", soll_block(lade_soll(), "### ", matrix=False), README)


def erzeuge_referenz(text: str) -> str:
    return _ersetze(text, "REFERENZSTAND", referenzstand_block(plugin_version()),
                    REFERENZ)


ERZEUGER = {README: erzeuge_readme, MATRIX: erzeuge_matrix, REFERENZ: erzeuge_referenz}


def _rel(pfad: Path) -> str:
    return pfad.relative_to(BASIS).as_posix()


# --- Konsistenz soll_katalog.json <-> befunde.KATALOG <-> Referenzkatalog ---

def _ids(text: str) -> set[str]:
    return {f"{praefix}-{nummer}" for praefix, nummern in ID_MUSTER.findall(text)
            for nummer in nummern.split("/")}


def _referenz_zeilen(text: str) -> dict[int, dict[str, str | None]]:
    """Checkbox-Zeilen des Referenzkatalogs je Kapitel: Text -> Klasse-Tag
    (None = ohne Tag, z. B. Kap. 17)."""
    zeilen: dict[int, dict[str, str | None]] = defaultdict(dict)
    kapitel: int | None = None
    kopf = re.compile(r"^# (\d+)\.\s")
    punkt = re.compile(r"^- \[ \] (?:\[([RPAX/]+)\] )?(.+?)\s*$")
    for zeile in text.splitlines():
        treffer = kopf.match(zeile)
        if treffer:
            kapitel = int(treffer.group(1))
            continue
        treffer = punkt.match(zeile)
        if treffer and kapitel is not None:
            zeilen[kapitel][treffer.group(2)] = treffer.group(1)
    return zeilen


def _klassen_vereinigung(tags: list[str | None]) -> str | None:
    buchstaben = {t for tag in tags if tag for t in tag.split("/")}
    return "/".join(b for b in KLASSE_REIHE if b in buchstaben) or None


def pruefe_soll(soll: dict, katalog, referenz_text: str | None) -> list[str]:
    """Strukturelle und fachliche Konsistenz der kanonischen Soll-Datei."""
    fehler: list[str] = []
    name = _rel(SOLL)
    # Kapitel
    kapitel = [k.get("nr") for k in soll["kapitel"]]
    if kapitel != list(KAPITEL):
        fehler.append(f"{name}: 'kapitel' muss genau die Nummern 1-20 in Reihenfolge fuehren")
    for kap in soll["kapitel"]:
        if not kap.get("titel"):
            fehler.append(f"{name}: Kapitel {kap.get('nr')} ohne 'titel'")
        if kap.get("nr") in (18, 19) and not kap.get("prosa"):
            fehler.append(f"{name}: Kapitel {kap.get('nr')} braucht 'prosa'")
    # Datenquellen
    quellen_keys = [q.get("key") for q in soll["datenquellen"]]
    if len(set(quellen_keys)) != len(quellen_keys) or not all(quellen_keys):
        fehler.append(f"{name}: 'datenquellen'-Schluessel fehlen oder sind doppelt")
    for quelle in soll["datenquellen"]:
        if not quelle.get("name") or not quelle.get("status") or "nr" not in quelle:
            fehler.append(f"{name}: Datenquelle {quelle.get('key')!r} unvollstaendig")
    # Punkte
    katalog_ids = {cid for cid, *_ in katalog}
    ids_gesehen: set[str] = set()
    checks_gesamt: set[str] = set()
    klasse_muster = re.compile(r"^(?:R|P|A|X)(?:/(?:P|A|X))*$")
    for punkt in soll["punkte"]:
        pid = str(punkt.get("id"))
        treffer = SOLL_ID.match(pid)
        if not treffer:
            fehler.append(f"{name}: ungueltige Soll-ID {pid!r} (Format Kxx.yy)")
            continue
        if pid in ids_gesehen:
            fehler.append(f"{name}: Soll-ID {pid} doppelt")
        ids_gesehen.add(pid)
        kap = punkt.get("kapitel")
        if kap not in PUNKT_KAPITEL or int(treffer.group(1)) != kap:
            fehler.append(f"{pid}: 'kapitel' {kap!r} passt nicht zur ID (Kap. 1-17)")
        status = punkt.get("status")
        if status not in STATUS:
            fehler.append(f"{pid}: unbekannter Status {status!r}")
            continue
        klasse = punkt.get("klasse")
        if klasse is None:
            if kap != 17:
                fehler.append(f"{pid}: 'klasse' fehlt (nur Kap. 17 ohne Klasse)")
        elif not klasse_muster.match(klasse) or \
                [KLASSE_REIHE.index(b) for b in klasse.split("/")] != \
                sorted(KLASSE_REIHE.index(b) for b in klasse.split("/")):
            fehler.append(f"{pid}: 'klasse' {klasse!r} ungueltig (R/P/A/X in dieser Reihenfolge)")
        if not punkt.get("punkt"):
            fehler.append(f"{pid}: 'punkt' fehlt")
        checks = punkt.get("checks") or []
        zusatz = punkt.get("zusatz") or ""
        umsetzung = punkt.get("umsetzung") or ""
        if status == "check" and not checks:
            fehler.append(f"{pid}: Status 'check' ohne 'checks'")
        if status in ("zusatz", "offen") and checks:
            fehler.append(f"{pid}: Status {status!r} darf keine 'checks' fuehren")
        if status == "ki" and not punkt.get("ki"):
            fehler.append(f"{pid}: Status 'ki' verlangt ki=true")
        if status != "zusatz" and not umsetzung:
            fehler.append(f"{pid}: 'umsetzung' fehlt")
        if status == "zusatz" and not zusatz:
            fehler.append(f"{pid}: Status 'zusatz' verlangt 'zusatz'-Text")
        if zusatz and PLUS not in zusatz and not zusatz.startswith("Ausbaustufe:"):
            fehler.append(f"{pid}: 'zusatz' muss die benoetigte Datenquelle mit {PLUS} nennen "
                          f"oder mit 'Ausbaustufe:' beginnen")
        if status == "zusatz" and PLUS not in zusatz:
            fehler.append(f"{pid}: Status 'zusatz' verlangt eine {PLUS}-Datenquelle im 'zusatz'-Text")
        text = " ".join([umsetzung, punkt.get("detail") or "", zusatz])
        unbekannt = sorted(set(checks) - katalog_ids)
        if unbekannt:
            fehler.append(f"{pid}: CHECK-IDs ohne Eintrag in befunde.KATALOG: {unbekannt}")
        ungenannt = sorted(set(checks) - _ids(text))
        if ungenannt:
            fehler.append(f"{pid}: 'checks' {ungenannt} werden im Umsetzungstext nicht genannt")
        checks_gesamt |= set(checks)
        if bool(punkt.get("ki")) != bool(KI_MUSTER.search(text)):
            fehler.append(f"{pid}: ki={punkt.get('ki')!r} passt nicht zum Text (nennt 'KI': "
                          f"{bool(KI_MUSTER.search(text))})")
        fremd = sorted(set(punkt.get("quellen") or []) - set(quellen_keys))
        if fremd:
            fehler.append(f"{pid}: unbekannte Datenquellen {fremd}")
    verwaist = sorted(katalog_ids - checks_gesamt)
    if verwaist:
        fehler.append(f"befunde.KATALOG: Checks ohne Soll-Punkt in {name}: {verwaist}")
    # Referenzkatalog: jede Checkbox-Zeile genau einmal, Klasse = Vereinigung
    if referenz_text is None:
        fehler.append(f"{_rel(REFERENZ)} fehlt (Referenzabgleich nicht moeglich)")
        return fehler
    referenz = _referenz_zeilen(referenz_text)
    zugeordnet: dict[tuple[int, str], list[str]] = defaultdict(list)
    for punkt in soll["punkte"]:
        pid, kap = punkt.get("id"), punkt.get("kapitel")
        tags: list[str | None] = []
        for zeile in punkt.get("referenz") or []:
            if zeile not in referenz.get(kap, {}):
                fehler.append(f"{pid}: Referenzzeile nicht in Kap. {kap} des "
                              f"Referenzkatalogs: {zeile!r}")
                continue
            zugeordnet[(kap, zeile)].append(pid)
            tags.append(referenz[kap][zeile])
        if punkt.get("referenz"):
            soll_klasse = _klassen_vereinigung(tags)
            if soll_klasse != punkt.get("klasse"):
                fehler.append(f"{pid}: Soll-Klasse {punkt.get('klasse')!r} != Vereinigung der "
                              f"Referenzklassen {soll_klasse!r}")
    for kap, zeilen in sorted(referenz.items()):
        for zeile in zeilen:
            anzahl = len(zugeordnet.get((kap, zeile), []))
            if anzahl != 1:
                fehler.append(f"Referenzkatalog Kap. {kap}: Zeile {anzahl}x zugeordnet "
                              f"(Soll genau 1x): {zeile!r}")
    return fehler


def _kapitel_ids(text: str, ueberschrift: str) -> dict[int, set[str]]:
    """CHECK-IDs je Katalogkapitel; `ueberschrift` = Markdown-Praefix ('### '/'## ')."""
    kapitel: dict[int, set[str]] = {}
    aktuell: int | None = None
    kopf = re.compile(rf"^{re.escape(ueberschrift)}(\d+)\.\s")
    for zeile in text.splitlines():
        treffer = kopf.match(zeile)
        if treffer:
            aktuell = int(treffer.group(1))
            kapitel[aktuell] = set()
            continue
        if re.match(r"^#{1,3} ", zeile):  # naechste (andere) Ueberschrift
            aktuell = None
        if aktuell is not None:
            kapitel[aktuell] |= _ids(zeile)
    return kapitel


def pruefe_katalog_ids() -> list[str]:
    """README-Pruefkatalog und Matrix: alle Kapitel 1-20 vorhanden, keine
    CHECK-ID ausserhalb von befunde.KATALOG."""
    fehler: list[str] = []
    for pfad in (README, MATRIX):
        if not pfad.is_file():
            fehler.append(f"{_rel(pfad)} fehlt")
    if fehler:
        return fehler
    katalog_ids = {cid for cid, *_ in _katalog()}
    for pfad, ueberschrift in ((README, "### "), (MATRIX, "## ")):
        kapitel = _kapitel_ids(pfad.read_text(encoding="utf-8"), ueberschrift)
        for kap in KAPITEL:
            if kap not in kapitel:
                fehler.append(f"{_rel(pfad)}: Katalogkapitel '{ueberschrift}{kap}.' fehlt")
        alle = set().union(*kapitel.values()) if kapitel else set()
        unbekannt = sorted(alle - katalog_ids)
        if unbekannt:
            fehler.append(f"{_rel(pfad)}: CHECK-IDs ohne Eintrag in befunde.KATALOG: "
                          f"{unbekannt}")
    return fehler


def pruefe() -> list[str]:
    """Build-Gate: liefert Fehlerliste, leer = Doku-Bloecke aktuell und
    Soll-Katalog/Katalog-IDs konsistent."""
    fehler: list[str] = []
    try:
        soll = lade_soll()
    except (ValueError, OSError, json.JSONDecodeError) as e:
        return [f"{_rel(SOLL)}: {e}"]
    referenz_text = REFERENZ.read_text(encoding="utf-8") if REFERENZ.is_file() else None
    fehler.extend(pruefe_soll(soll, _katalog(), referenz_text))
    if fehler:
        return fehler  # erst die Quelle reparieren, dann generieren
    for pfad, erzeuger in ERZEUGER.items():
        if not pfad.is_file():
            fehler.append(f"{_rel(pfad)} fehlt")
            continue
        ist = pfad.read_text(encoding="utf-8")
        try:
            soll_text = erzeuger(ist)
        except (ValueError, OSError, json.JSONDecodeError, KeyError) as e:
            fehler.append(f"{_rel(pfad)}: {e}")
            continue
        if ist != soll_text:
            fehler.append(f"{_rel(pfad)}: generierte Bloecke weichen vom "
                          "Sollstand ab (soll_katalog.json / befunde.KATALOG / "
                          "erwartung.json / plugin.json) - "
                          "`py werkzeuge/katalog_doku.py --write` ausfuehren")
    fehler.extend(pruefe_katalog_ids())
    return fehler


def main(argv: list[str]) -> int:
    if argv == ["--check"]:
        fehler = pruefe()
        for f in fehler:
            print(f"FEHLER: {f}", file=sys.stderr)
        if not fehler:
            print("Katalog-Doku aktuell (Soll-Katalog README/Matrix, Ebenen-Tabelle, "
                  "Check-Register, Referenzstand) und Soll-Katalog konsistent "
                  "(soll_katalog.json / befunde.KATALOG / Referenzkatalog).")
        return 1 if fehler else 0
    if argv == ["--write"]:
        soll = lade_soll()
        referenz_text = REFERENZ.read_text(encoding="utf-8") if REFERENZ.is_file() else None
        fehler = pruefe_soll(soll, _katalog(), referenz_text)
        if fehler:
            for f in fehler:
                print(f"FEHLER: {f}", file=sys.stderr)
            print("soll_katalog.json inkonsistent - nichts geschrieben.", file=sys.stderr)
            return 1
        for pfad, erzeuger in ERZEUGER.items():
            ist = pfad.read_text(encoding="utf-8")
            neu = erzeuger(ist)
            if neu != ist:
                pfad.write_text(neu, encoding="utf-8", newline="\n")
                print(f"geschrieben: {_rel(pfad)}")
            else:
                print(f"unveraendert: {_rel(pfad)}")
        fehler = pruefe_katalog_ids()
        for f in fehler:
            print(f"FEHLER: {f}", file=sys.stderr)
        return 1 if fehler else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
