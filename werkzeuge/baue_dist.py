"""Baut die Distributionspakete in dist/ aus dem Repo-Stand.

  py werkzeuge/baue_dist.py

Erzeugt:
  dist/jahresabschluss-agent_GitHub.zip  Repo-Abbild (ohne dist/,
                                         testdaten/ausgabe/, __pycache__)
  dist/jahresabschluss-agent.plugin      Plugin-Paket (.claude-plugin,
                                         skills, werkzeuge, README, LICENSE)

Grund fuer dieses Skript statt Compress-Archive (Windows PowerShell 5.1):
ZIP-Eintraege muessen Forward-Slashes als Pfadtrenner tragen (PKWARE
APPNOTE 4.4.17.1, https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT);
Python zipfile schreibt sie so und setzt fuer Nicht-ASCII-Dateinamen das
UTF-8-Flag - Compress-Archive tut beides nicht (Backslash-Eintraege,
OEM-kodierte Umlaute, entpackt unter Linux/macOS fehlerhaft).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
DIST = BASIS / "dist"

AUSSCHLUSS_ORDNER = {"__pycache__", "dist", ".git", "JA-Pruefung"}
AUSSCHLUSS_PFADE = [("testdaten", "ausgabe")]  # generierte Prueflaeufe
PLUGIN_WURZELN = {".claude-plugin", "skills", "werkzeuge"}
PLUGIN_WURZELDATEIEN = {"README.md", "LICENSE"}


def _relevant(rel: Path) -> bool:
    teile = rel.parts
    if any(t in AUSSCHLUSS_ORDNER for t in teile):
        return False
    if any(teile[: len(p)] == p for p in AUSSCHLUSS_PFADE):
        return False
    return not (rel.name.startswith("~$") or rel.suffix == ".pyc")


def _schreibe(ziel: Path, dateien: list[Path]) -> None:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        for datei in sorted(dateien):
            z.write(datei, datei.relative_to(BASIS).as_posix())
    print(f"gebaut: {ziel.name} ({len(dateien)} Dateien, "
          f"{ziel.stat().st_size:,} Bytes)".replace(",", "."))


def main() -> int:
    alle = [p for p in BASIS.rglob("*")
            if p.is_file() and _relevant(p.relative_to(BASIS))]
    _schreibe(DIST / "jahresabschluss-agent_GitHub.zip", alle)
    plugin = [p for p in alle
              if p.relative_to(BASIS).parts[0] in PLUGIN_WURZELN
              or (len(p.relative_to(BASIS).parts) == 1
                  and p.name in PLUGIN_WURZELDATEIEN)]
    _schreibe(DIST / "jahresabschluss-agent.plugin", plugin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
