"""Baut die Distributionspakete in dist/ aus dem Repo-Stand.

  py werkzeuge/baue_dist.py

Erzeugt:
  dist/jahresabschluss-agent_GitHub.zip  Repo-Abbild (ohne dist/,
                                         testdaten/ausgabe/, __pycache__)
  dist/jahresabschluss-agent.plugin      Plugin-Paket (.claude-plugin,
                                         skills, werkzeuge, README, LICENSE)

Vor dem Bau laeuft eine Release-Validierung: Pflichtmanifeste
.claude-plugin/plugin.json und .claude-plugin/marketplace.json vorhanden
und gueltiges JSON, Pluginname in beiden Manifesten identisch, Version in
plugin.json synchron zu VERSION in werkzeuge/ja_pruefung.py, SKILL.md mit
Frontmatter vorhanden. Nach dem Bau wird der Plugin-Archivinhalt geprueft
(Pflichteintraege enthalten, Ausschluesse nicht enthalten). Jeder Verstoss
bricht mit Exit-Code 1 ab - ein erfolgreicher Build garantiert damit die
Sollstruktur der Claude-Code-Plugin-Spezifikation
(https://code.claude.com/docs/en/plugins-reference).

Grund fuer dieses Skript statt Compress-Archive (Windows PowerShell 5.1):
ZIP-Eintraege muessen Forward-Slashes als Pfadtrenner tragen (PKWARE
APPNOTE 4.4.17.1, https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT);
Python zipfile schreibt sie so und setzt fuer Nicht-ASCII-Dateinamen das
UTF-8-Flag - Compress-Archive tut beides nicht (Backslash-Eintraege,
OEM-kodierte Umlaute, entpackt unter Linux/macOS fehlerhaft).
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
DIST = BASIS / "dist"

AUSSCHLUSS_ORDNER = {"__pycache__", "dist", ".git", "JA-Pruefung"}
AUSSCHLUSS_PFADE = [("testdaten", "ausgabe")]  # generierte Prueflaeufe
PLUGIN_WURZELN = {".claude-plugin", "skills", "werkzeuge"}
PLUGIN_WURZELDATEIEN = {"README.md", "LICENSE"}
MANIFEST_PLUGIN = Path(".claude-plugin") / "plugin.json"
MANIFEST_MARKT = Path(".claude-plugin") / "marketplace.json"
SKILL = Path("skills") / "ja-pruefung" / "SKILL.md"


def validiere_repo() -> list[str]:
    """Prueft die Plugin-Sollstruktur vor dem Bau; liefert Fehlerliste."""
    fehler: list[str] = []

    def _json(rel: Path) -> dict | None:
        pfad = BASIS / rel
        if not pfad.is_file():
            fehler.append(f"{rel.as_posix()} fehlt (Pflichtdatei der "
                          "Plugin-Spezifikation)")
            return None
        try:
            return json.loads(pfad.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            fehler.append(f"{rel.as_posix()}: kein gueltiges JSON ({e})")
            return None

    plugin = _json(MANIFEST_PLUGIN)
    markt = _json(MANIFEST_MARKT)

    # Altlast abfangen: endungslose Manifeste blockieren die Installation
    for alt in ("plugin", "marketplace"):
        if (BASIS / ".claude-plugin" / alt).exists():
            fehler.append(f".claude-plugin/{alt}: endungslose Manifestdatei "
                          f"- in {alt}.json umbenennen")

    if plugin is not None:
        for feld in ("name", "version", "description"):
            if not plugin.get(feld):
                fehler.append(f"plugin.json: Feld '{feld}' fehlt oder leer")
        quelle = (BASIS / "werkzeuge" / "ja_pruefung.py").read_text(
            encoding="utf-8")
        treffer = re.search(r'^VERSION\s*=\s*"([^"]+)"', quelle, re.M)
        if not treffer:
            fehler.append("werkzeuge/ja_pruefung.py: VERSION-Konstante "
                          "nicht gefunden")
        elif plugin.get("version") != treffer.group(1):
            fehler.append(
                f"Versionsdrift: plugin.json {plugin.get('version')!r} != "
                f"ja_pruefung.py VERSION {treffer.group(1)!r}")

    if plugin is not None and markt is not None:
        namen = [p.get("name") for p in markt.get("plugins", [])]
        if plugin.get("name") not in namen:
            fehler.append(
                f"marketplace.json: Plugin {plugin.get('name')!r} nicht "
                f"unter 'plugins' gelistet (gefunden: {namen})")

    if not (BASIS / SKILL).is_file():
        fehler.append(f"{SKILL.as_posix()} fehlt")
    else:
        inhalt = (BASIS / SKILL).read_text(encoding="utf-8")
        if not inhalt.startswith("---") or inhalt.count("---") < 2:
            fehler.append(f"{SKILL.as_posix()}: YAML-Frontmatter "
                          "(--- ... ---) fehlt")
        else:
            frontmatter = inhalt.split("---", 2)[1]
            for feld in ("name:", "description:"):
                if feld not in frontmatter:
                    fehler.append(f"{SKILL.as_posix()}-Frontmatter: "
                                  f"'{feld}' fehlt")
    return fehler


def validiere_archiv(ziel: Path) -> list[str]:
    """Prueft den fertigen Plugin-Archivinhalt; liefert Fehlerliste."""
    fehler: list[str] = []
    with zipfile.ZipFile(ziel) as z:
        eintraege = set(z.namelist())
    for pflicht in (MANIFEST_PLUGIN.as_posix(), MANIFEST_MARKT.as_posix(),
                    SKILL.as_posix(), "werkzeuge/ja_pruefung.py",
                    "README.md", "LICENSE"):
        if pflicht not in eintraege:
            fehler.append(f"{ziel.name}: Pflichteintrag {pflicht} fehlt")
    verboten = sorted(e for e in eintraege
                      if any(t in Path(e).parts
                             for t in ("__pycache__", "dist", "ausgabe")))
    if verboten:
        fehler.append(f"{ziel.name}: ausgeschlossene Pfade enthalten: "
                      + ", ".join(verboten[:5]))
    return fehler


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
    fehler = validiere_repo()
    if fehler:
        for f in fehler:
            print(f"FEHLER: {f}", file=sys.stderr)
        print("Build abgebrochen - Sollstruktur zuerst herstellen.",
              file=sys.stderr)
        return 1
    alle = [p for p in BASIS.rglob("*")
            if p.is_file() and _relevant(p.relative_to(BASIS))]
    _schreibe(DIST / "jahresabschluss-agent_GitHub.zip", alle)
    plugin = [p for p in alle
              if p.relative_to(BASIS).parts[0] in PLUGIN_WURZELN
              or (len(p.relative_to(BASIS).parts) == 1
                  and p.name in PLUGIN_WURZELDATEIEN)]
    ziel = DIST / "jahresabschluss-agent.plugin"
    _schreibe(ziel, plugin)
    fehler = validiere_archiv(ziel)
    if fehler:
        for f in fehler:
            print(f"FEHLER: {f}", file=sys.stderr)
        return 1
    print("Release-Validierung: Manifeste, Versionsgleichlauf, SKILL-"
          "Frontmatter und Archivinhalt geprueft - keine Befunde.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
