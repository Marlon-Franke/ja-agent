"""Generiert die aus befunde.KATALOG bzw. plugin.json abgeleiteten Doku-
Bloecke und prueft die Konsistenz der Katalog-Dokumentation.

  py werkzeuge/katalog_doku.py --write   Bloecke neu schreiben
  py werkzeuge/katalog_doku.py --check   nur pruefen (Exit 1 bei Drift)

Generierte Bloecke (Marker, Inhalt dazwischen wird ersetzt):
  skills/ja-pruefung/references/pruefkatalog.md
    <!-- KATALOG:EBENEN:START --> ... END     Ebenen-Tabelle (Ebene -> Checks)
    <!-- KATALOG:REGISTER:START --> ... END   Check-Register (ID, Name,
                                              Bereich, Ebene, Klasse)
  Pruefkatalog fuer einen Python-basierten Accounting-Agenten.md
    <!-- KATALOG:REFERENZSTAND:START --> ... END   Referenzversion = Plugin-
                                              Version (Revisionsbefund P2.1)

Konsistenzpruefung (pruefe(), Build-Gate in baue_dist.py, Revisionsbefund
P1.5): README-Checkliste (### 1. ... ### 20.), Abdeckungsmatrix (## 1. ...
## 20.) und befunde.KATALOG muessen dieselben CHECK-IDs fuehren - je Kapitel
dieselbe ID-Menge in README und Matrix, jede KATALOG-ID in beiden Dokumenten
referenziert, keine ID ausserhalb des KATALOGs. Damit kann eine Zuordnung
nicht mehr nur in einem der beiden Dokumente geaendert werden. (Die
vollstaendige Kanonisierung der Soll-Katalogpunkte mit eigener stabiler ID
bleibt Ausbaustufe; siehe docs/test-strategy.md.)

Semantik (Klaerung der Klassifikationsdrift, Release-Readiness-Report
Befunde 5-9): Die [R]/[P]/[A]/[X]-Tags an den Katalogpunkten in README und
Matrix sind die Klasse des SOLL-Katalogpunkts (1:1 aus dem Referenzkatalog
"Pruefkatalog fuer einen Python-basierten Accounting-Agenten.md"). Ebene und
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
KAPITEL = range(1, 21)  # Katalogkapitel 1-20 in README und Matrix


def _katalog():
    sys.path.insert(0, str(BASIS / "werkzeuge"))
    try:
        import befunde  # noqa: PLC0415
    finally:
        sys.path.pop(0)
    return befunde.KATALOG


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


def register_tabelle(katalog) -> str:
    zeilen = ["| ID | Check | Bereich | Ebene | Klasse |", "|---|---|---|---|---|"]
    for cid, name, bereich, ebene, klasse in katalog:
        basis, *zusatz = klasse.split("/")
        klasse_txt = f"{basis} ({KLASSEN[basis]})" + (" +X Zusatzdaten" if zusatz else "")
        zeilen.append(f"| {cid} | {name} | {bereich} | {ebene} | {klasse_txt} |")
    zeilen.append("")
    zeilen.append(f"{len(katalog)} Checks (= `len(befunde.KATALOG)`).")
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


def _bloecke_matrix(katalog) -> dict[str, str]:
    return {"EBENEN": ebenen_tabelle(katalog), "REGISTER": register_tabelle(katalog)}


def _ersetze(text: str, name: str, inhalt: str, datei: Path) -> str:
    # Block darf leer sein (frisch gesetzte Marker); Ersetzung ist idempotent.
    muster = re.compile(rf"(<!-- KATALOG:{name}:START -->\n).*?(<!-- KATALOG:{name}:END -->)",
                        re.S)
    if not muster.search(text):
        raise ValueError(f"Marker KATALOG:{name}:START/END fehlt in {datei.name}")
    return muster.sub(lambda m: m.group(1) + inhalt + "\n" + m.group(2), text, count=1)


def erzeuge_matrix(text: str) -> str:
    katalog = _katalog()
    for name, inhalt in _bloecke_matrix(katalog).items():
        text = _ersetze(text, name, inhalt, MATRIX)
    return text


def erzeuge_referenz(text: str) -> str:
    return _ersetze(text, "REFERENZSTAND", referenzstand_block(plugin_version()),
                    REFERENZ)


ERZEUGER = {MATRIX: erzeuge_matrix, REFERENZ: erzeuge_referenz}


def _rel(pfad: Path) -> str:
    return pfad.relative_to(BASIS).as_posix()


# --- Konsistenz README-Checkliste <-> Abdeckungsmatrix <-> befunde.KATALOG ---

def _ids(text: str) -> set[str]:
    return {f"{praefix}-{nummer}" for praefix, nummern in ID_MUSTER.findall(text)
            for nummer in nummern.split("/")}


def _kapitel_ids(text: str, ueberschrift: str) -> dict[int, set[str]]:
    """IDs je Katalogkapitel; `ueberschrift` = Markdown-Praefix ('### '/'## ')."""
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
    fehler: list[str] = []
    for pfad in (README, MATRIX):
        if not pfad.is_file():
            fehler.append(f"{_rel(pfad)} fehlt")
    if fehler:
        return fehler
    katalog_ids = {cid for cid, *_ in _katalog()}
    readme = _kapitel_ids(README.read_text(encoding="utf-8"), "### ")
    matrix = _kapitel_ids(MATRIX.read_text(encoding="utf-8"), "## ")
    for kap in KAPITEL:
        if kap not in readme:
            fehler.append(f"README.md: Katalogkapitel '### {kap}.' fehlt")
        if kap not in matrix:
            fehler.append(f"{_rel(MATRIX)}: Katalogkapitel '## {kap}.' fehlt")
        if kap in readme and kap in matrix and readme[kap] != matrix[kap]:
            nur_r = sorted(readme[kap] - matrix[kap])
            nur_m = sorted(matrix[kap] - readme[kap])
            fehler.append(
                f"Katalogdrift Kapitel {kap}: CHECK-IDs nur in README {nur_r}, "
                f"nur in Matrix {nur_m} - beide Dokumente angleichen")
    alle_r = set().union(*readme.values()) if readme else set()
    alle_m = set().union(*matrix.values()) if matrix else set()
    for name, ids in (("README.md", alle_r), (_rel(MATRIX), alle_m)):
        unbekannt = sorted(ids - katalog_ids)
        if unbekannt:
            fehler.append(f"{name}: CHECK-IDs ohne Eintrag in befunde.KATALOG: "
                          f"{unbekannt}")
        fehlend = sorted(katalog_ids - ids)
        if fehlend:
            fehler.append(f"{name}: KATALOG-Checks ohne Katalogpunkt-Zuordnung: "
                          f"{fehlend}")
    return fehler


def pruefe() -> list[str]:
    """Build-Gate: liefert Fehlerliste, leer = Doku-Bloecke aktuell und
    Katalog-IDs konsistent."""
    fehler: list[str] = []
    for pfad, erzeuger in ERZEUGER.items():
        if not pfad.is_file():
            fehler.append(f"{_rel(pfad)} fehlt")
            continue
        ist = pfad.read_text(encoding="utf-8")
        try:
            soll = erzeuger(ist)
        except (ValueError, OSError, json.JSONDecodeError) as e:
            fehler.append(str(e))
            continue
        if ist != soll:
            fehler.append(f"{_rel(pfad)}: generierte Bloecke weichen vom "
                          "Sollstand ab (befunde.KATALOG / plugin.json) - "
                          "`py werkzeuge/katalog_doku.py --write` ausfuehren")
    fehler.extend(pruefe_katalog_ids())
    return fehler


def main(argv: list[str]) -> int:
    if argv == ["--check"]:
        fehler = pruefe()
        for f in fehler:
            print(f"FEHLER: {f}", file=sys.stderr)
        if not fehler:
            print("Katalog-Doku aktuell (Ebenen-Tabelle, Check-Register, "
                  "Referenzstand) und Katalog-IDs konsistent "
                  "(README/Matrix/KATALOG).")
        return 1 if fehler else 0
    if argv == ["--write"]:
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
