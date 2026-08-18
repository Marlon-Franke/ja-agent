"""Vergleicht einen Pipeline-Lauf mit dem maschinenlesbaren Erwartungsbild
testdaten/erwartung.json (Revisionsbefund P1.2: vollstaendige Verteilung
aller Check-IDs und Schweregrade statt Summen-Grep).

  py werkzeuge/pruefe_erwartung.py --lauf standard --ausgabe testdaten/ausgabe
        [--protokoll lauf.txt] [--erwartung testdaten/erwartung.json]

Geprueft werden je Lauf:
  * jede Check-ID aus befunde.KATALOG hat eine (ggf. vom Basislauf geerbte)
    Erwartung; keine Erwartung ohne Katalogeintrag;
  * status "aktiv": ID nicht unter nicht_pruefbar, Trefferzahl je Schwere
    exakt wie erwartet (fehlende Schwere = 0 = expliziter Nullbefund);
  * status "skip": ID unter nicht_pruefbar mit erwartetem Grund (Teilstring),
    keine Befunde;
  * "belege" (optional): sortierte Belegfeld-1-Werte der Treffer identisch;
  * Summen je Schwere, KI-Kandidatenzahl (llm_kandidaten.json);
  * optional das stdout-Protokoll: Summenzeile, Checkzahl im Kopf, keine
    "WARNUNG: Bilanzprobe"-Zeile.
Exit 0 = Lauf entspricht dem Erwartungsbild, 1 = Abweichungen (Liste auf
stderr), 2 = Aufruffehler. Importierbar: vergleiche_lauf(...) liefert die
Abweichungsliste; release_check.py nutzt sie fuer die drei Referenzlaeufe.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
ERWARTUNG = BASIS / "testdaten" / "erwartung.json"
SCHWEREN = ("hoch", "mittel", "hinweis")


def lade_erwartung(pfad: Path = ERWARTUNG) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8"))


def effektiver_lauf(erwartung: dict, name: str) -> dict:
    """Lauf mit aufgeloester 'basis'-Vererbung (Checks des Basislaufs +
    Abweichungen des Laufs)."""
    laeufe = erwartung["laeufe"]
    if name not in laeufe:
        raise KeyError(f"Lauf {name!r} nicht in erwartung.json "
                       f"(vorhanden: {', '.join(laeufe)})")
    lauf = copy.deepcopy(laeufe[name])
    basis = lauf.pop("basis", None)
    if basis:
        checks = copy.deepcopy(effektiver_lauf(erwartung, basis)["checks"])
        checks.update(lauf.get("checks", {}))
        lauf["checks"] = checks
    return lauf


def _katalog_ids() -> list[str]:
    sys.path.insert(0, str(BASIS / "werkzeuge"))
    try:
        import befunde  # noqa: PLC0415
    finally:
        sys.path.pop(0)
    return [cid for cid, *_ in befunde.KATALOG]


def vergleiche_lauf(name: str, ausgabe: Path, protokoll: str | None = None,
                    erwartung: dict | None = None) -> list[str]:
    """Liefert die Liste der Abweichungen (leer = Lauf entspricht Erwartung)."""
    erwartung = erwartung or lade_erwartung()
    lauf = effektiver_lauf(erwartung, name)
    fehler: list[str] = []
    praefix = f"[{name}]"

    befunde_pfad = ausgabe / "befunde.json"
    kandidaten_pfad = ausgabe / "llm_kandidaten.json"
    for pfad in (befunde_pfad, kandidaten_pfad):
        if not pfad.is_file():
            return [f"{praefix} {pfad} fehlt - Lauf nicht ausgefuehrt?"]
    daten = json.loads(befunde_pfad.read_text(encoding="utf-8"))
    kandidaten = json.loads(kandidaten_pfad.read_text(encoding="utf-8"))

    katalog = _katalog_ids()
    soll_checks: dict[str, dict] = lauf["checks"]
    if erwartung.get("katalog_checks") not in (None, len(katalog)):
        fehler.append(f"{praefix} erwartung.json nennt {erwartung['katalog_checks']} "
                      f"Katalog-Checks, befunde.KATALOG hat {len(katalog)}")
    for cid in katalog:
        if cid not in soll_checks:
            fehler.append(f"{praefix} keine Erwartung fuer Katalog-Check {cid}")
    for cid in soll_checks:
        if cid not in katalog:
            fehler.append(f"{praefix} Erwartung fuer unbekannte Check-ID {cid}")

    zaehl: dict[str, Counter] = defaultdict(Counter)
    belege: dict[str, list[str]] = defaultdict(list)
    for f in daten.get("befunde", []):
        zaehl[f["check_id"]][f["schwere"]] += 1
        if f.get("beleg"):
            belege[f["check_id"]].append(f["beleg"])
    skips: dict[str, str] = daten.get("nicht_pruefbar", {})
    for cid in katalog:
        soll = soll_checks.get(cid)
        if soll is None:
            continue
        status = soll.get("status")
        ist_treffer = {s: zaehl[cid][s] for s in SCHWEREN if zaehl[cid][s]}
        if status == "aktiv":
            if cid in skips:
                fehler.append(f"{praefix} {cid}: erwartet aktiv, ist uebersprungen "
                              f"({skips[cid]})")
            soll_treffer = {s: n for s, n in soll.get("treffer", {}).items() if n}
            if ist_treffer != soll_treffer:
                fehler.append(f"{praefix} {cid}: Treffer erwartet {soll_treffer or 'keine'}, "
                              f"ist {ist_treffer or 'keine'}")
            if "belege" in soll and sorted(belege[cid]) != sorted(soll["belege"]):
                fehler.append(f"{praefix} {cid}: Belege erwartet {sorted(soll['belege'])}, "
                              f"ist {sorted(belege[cid])}")
        elif status == "skip":
            if cid not in skips:
                fehler.append(f"{praefix} {cid}: erwartet uebersprungen "
                              f"({soll.get('grund', '')}), ist aktiv")
            elif soll.get("grund") and soll["grund"] not in skips[cid]:
                fehler.append(f"{praefix} {cid}: Skip-Grund erwartet '{soll['grund']}', "
                              f"ist '{skips[cid]}'")
            if ist_treffer:
                fehler.append(f"{praefix} {cid}: uebersprungen erwartet, aber Befunde "
                              f"{ist_treffer}")
        else:
            fehler.append(f"{praefix} {cid}: unbekannter Erwartungsstatus {status!r}")
    for cid in skips:
        if cid not in katalog:
            fehler.append(f"{praefix} nicht_pruefbar nennt unbekannte Check-ID {cid}")

    ist_summen = Counter(f["schwere"] for f in daten.get("befunde", []))
    soll_summen = lauf.get("summen", {})
    for s in SCHWEREN:
        if ist_summen[s] != soll_summen.get(s, 0):
            fehler.append(f"{praefix} Summe {s}: erwartet {soll_summen.get(s, 0)}, "
                          f"ist {ist_summen[s]}")
    ki_soll = lauf.get("ki_kandidaten")
    ki_ist = kandidaten.get("kandidaten_gesamt")
    if ki_soll is not None and (ki_ist != ki_soll
                                or len(kandidaten.get("kandidaten", [])) != ki_soll):
        fehler.append(f"{praefix} KI-Kandidaten: erwartet {ki_soll}, ist {ki_ist} "
                      f"(exportiert {len(kandidaten.get('kandidaten', []))})")

    if protokoll is not None:
        summenzeile = (f"Befunde: {soll_summen.get('hoch', 0)} hoch / "
                       f"{soll_summen.get('mittel', 0)} mittel / "
                       f"{soll_summen.get('hinweis', 0)} Hinweise | "
                       f"KI-Kandidaten: {ki_soll}")
        if summenzeile not in protokoll:
            fehler.append(f"{praefix} stdout: Summenzeile '{summenzeile}' fehlt")
        if f"({len(katalog)} Checks)" not in protokoll:
            fehler.append(f"{praefix} stdout: Kopfzeile nennt nicht "
                          f"'({len(katalog)} Checks)'")
        if "WARNUNG: Bilanzprobe" in protokoll:
            fehler.append(f"{praefix} stdout: 'WARNUNG: Bilanzprobe' darf nie auftreten")
    return fehler


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--lauf", required=True, help="Laufname aus erwartung.json")
    p.add_argument("--ausgabe", required=True, type=Path,
                   help="Ausgabeordner des Laufs (befunde.json, llm_kandidaten.json)")
    p.add_argument("--protokoll", type=Path,
                   help="stdout-Protokoll des Laufs (optional)")
    p.add_argument("--erwartung", type=Path, default=ERWARTUNG)
    args = p.parse_args(argv)
    try:
        erwartung = lade_erwartung(args.erwartung)
        protokoll = (args.protokoll.read_text(encoding="utf-8", errors="replace")
                     if args.protokoll else None)
        fehler = vergleiche_lauf(args.lauf, args.ausgabe, protokoll, erwartung)
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 2
    for f in fehler:
        print(f"ABWEICHUNG: {f}", file=sys.stderr)
    if fehler:
        print(f"Lauf '{args.lauf}': {len(fehler)} Abweichung(en) vom Erwartungsbild.",
              file=sys.stderr)
        return 1
    lauf = effektiver_lauf(erwartung, args.lauf)
    print(f"Lauf '{args.lauf}' entspricht dem Erwartungsbild: "
          f"{len(lauf['checks'])} Checks geprueft, Summen {lauf['summen']}, "
          f"KI-Kandidaten {lauf['ki_kandidaten']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
