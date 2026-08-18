"""Generiert die aus befunde.KATALOG abgeleiteten Doku-Bloecke der
Abdeckungsmatrix (skills/ja-pruefung/references/pruefkatalog.md).

  py werkzeuge/katalog_doku.py --write   Bloecke neu schreiben
  py werkzeuge/katalog_doku.py --check   nur pruefen (Exit 1 bei Drift)

Bloecke (Marker in pruefkatalog.md, Inhalt dazwischen wird ersetzt):
  <!-- KATALOG:EBENEN:START --> ... END     Ebenen-Tabelle (Ebene -> Checks)
  <!-- KATALOG:REGISTER:START --> ... END   Check-Register (ID, Name, Bereich,
                                            Ebene, Klasse) in Katalogreihenfolge

Semantik (Klaerung der Klassifikationsdrift, Release-Readiness-Report
Befunde 5-9): Die [R]/[P]/[A]/[X]-Tags an den Katalogpunkten in README und
Matrix sind die Klasse des SOLL-Katalogpunkts (1:1 aus dem Referenzkatalog
"Pruefkatalog fuer einen Python-basierten Accounting-Agenten.md"). Ebene und
Klasse des IMPLEMENTIERTEN Checks fuehrt allein befunde.KATALOG - sie
steuern Bericht und Excel/PBI-Ausweis. Beides darf abweichen (ein P-Check
kann einen R-Katalogpunkt abdecken); die implementierte Sicht wird deshalb
hier generiert statt von Hand gepflegt. baue_dist.py ruft pruefe() als
Build-Gate auf.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
MATRIX = BASIS / "skills" / "ja-pruefung" / "references" / "pruefkatalog.md"
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


def _bloecke(katalog) -> dict[str, str]:
    return {"EBENEN": ebenen_tabelle(katalog), "REGISTER": register_tabelle(katalog)}


def _ersetze(text: str, name: str, inhalt: str) -> str:
    # Block darf leer sein (frisch gesetzte Marker); Ersetzung ist idempotent.
    muster = re.compile(rf"(<!-- KATALOG:{name}:START -->\n).*?(<!-- KATALOG:{name}:END -->)",
                        re.S)
    if not muster.search(text):
        raise ValueError(f"Marker KATALOG:{name}:START/END fehlt in {MATRIX.name}")
    return muster.sub(lambda m: m.group(1) + inhalt + "\n" + m.group(2), text, count=1)


def erzeuge(text: str) -> str:
    katalog = _katalog()
    for name, inhalt in _bloecke(katalog).items():
        text = _ersetze(text, name, inhalt)
    return text


def pruefe() -> list[str]:
    """Build-Gate: liefert Fehlerliste, leer = Matrix-Bloecke aktuell."""
    if not MATRIX.is_file():
        return [f"{MATRIX.relative_to(BASIS).as_posix()} fehlt"]
    ist = MATRIX.read_text(encoding="utf-8")
    try:
        soll = erzeuge(ist)
    except ValueError as e:
        return [str(e)]
    if ist != soll:
        return [f"{MATRIX.relative_to(BASIS).as_posix()}: generierte Bloecke "
                "(Ebenen-Tabelle/Check-Register) weichen von befunde.KATALOG ab "
                "- `py werkzeuge/katalog_doku.py --write` ausfuehren"]
    return []


def main(argv: list[str]) -> int:
    if argv == ["--check"]:
        fehler = pruefe()
        for f in fehler:
            print(f"FEHLER: {f}", file=sys.stderr)
        if not fehler:
            print("Katalog-Doku aktuell (Ebenen-Tabelle, Check-Register).")
        return 1 if fehler else 0
    if argv == ["--write"]:
        ist = MATRIX.read_text(encoding="utf-8")
        neu = erzeuge(ist)
        if neu != ist:
            MATRIX.write_text(neu, encoding="utf-8")
            print(f"geschrieben: {MATRIX.relative_to(BASIS).as_posix()}")
        else:
            print("Katalog-Doku unveraendert.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
