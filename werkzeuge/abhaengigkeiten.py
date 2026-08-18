"""Preflight fuer Python-Drittpakete der Pipeline (Revisionsbefund P0.1).

Die Plugin-Installation von Claude Code installiert keine Python-Pakete;
ohne diesen Preflight bricht die Pipeline in einer frischen Umgebung mit
einem nackten ``ModuleNotFoundError: No module named 'openpyxl'`` ab. Hier
wird stattdessen VOR dem Import der abhaengigen Module geprueft und mit
klarem Installationshinweis beendet - es wird nichts unbemerkt installiert.

Verwendung (in ja_pruefung.py und llm_einarbeiten.py nach parse_args, damit
``--help`` auch ohne installierte Pakete funktioniert)::

    import abhaengigkeiten
    abhaengigkeiten.pruefe_oder_beende()      # Exit 2 bei fehlenden Paketen

Einzige Quelle der Pflichtpakete ist requirements.txt (Repo- und
Plugin-Wurzel); PAKETE listet die Importnamen dazu.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Importname -> Zweck (nur Pflichtpakete; Versionsspanne steht in requirements.txt)
PAKETE: dict[str, str] = {
    "openpyxl": "Excel-Pruefbericht schreiben/einarbeiten",
}
EXIT_FEHLENDE_ABHAENGIGKEIT = 2

WURZEL = Path(__file__).resolve().parents[1]
REQUIREMENTS = WURZEL / "requirements.txt"


def fehlende_pakete(pakete: dict[str, str] | None = None) -> list[str]:
    """Importnamen, fuer die kein Modul auffindbar ist (ohne zu importieren)."""
    return [name for name in (pakete or PAKETE)
            if importlib.util.find_spec(name) is None]


def installationshinweis(fehlend: list[str]) -> str:
    zeilen = ["FEHLER: Python-Paket(e) nicht installiert: "
              + ", ".join(f"{n} ({PAKETE.get(n, 'Pflichtpaket')})" for n in fehlend),
              "Installation (einmalig, in der Python-Umgebung, die die Pipeline ausfuehrt):",
              f'  "{sys.executable}" -m pip install -r "{REQUIREMENTS}"']
    if not REQUIREMENTS.is_file():
        zeilen.append(f"  Hinweis: {REQUIREMENTS.name} fehlt neben werkzeuge/ - "
                      "Paket unvollstaendig; requirements.txt aus dem Repository "
                      "https://github.com/Marlon-Franke/ja-agent verwenden.")
    zeilen.append(f"Es wird nichts automatisch installiert (Exit {EXIT_FEHLENDE_ABHAENGIGKEIT}).")
    return "\n".join(zeilen)


def pruefe_oder_beende(pakete: dict[str, str] | None = None) -> None:
    """Beendet den Prozess mit klarer Meldung, wenn Pflichtpakete fehlen."""
    fehlend = fehlende_pakete(pakete)
    if fehlend:
        print(installationshinweis(fehlend), file=sys.stderr)
        raise SystemExit(EXIT_FEHLENDE_ABHAENGIGKEIT)


if __name__ == "__main__":
    fehlt = fehlende_pakete()
    if fehlt:
        print(installationshinweis(fehlt), file=sys.stderr)
        raise SystemExit(EXIT_FEHLENDE_ABHAENGIGKEIT)
    print("Laufzeitabhaengigkeiten vorhanden: " + ", ".join(PAKETE))
