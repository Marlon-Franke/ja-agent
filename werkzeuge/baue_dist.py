"""Baut die Distributionspakete in dist/ aus dem Repo-Stand.

  py werkzeuge/baue_dist.py

Erzeugt:
  dist/jahresabschluss-agent_GitHub.zip  Repo-Abbild (alle von Git
                                         versionierten Dateien)
  dist/jahresabschluss-agent.plugin      Plugin-Paket (.claude-plugin,
                                         skills, werkzeuge, README, LICENSE)

Dateiquelle ist der Git-Index (`git ls-files`), nicht das Dateisystem:
ungetrackte Streudateien im Arbeitsbaum (lokale Berichte, ZIPs, Prueflaeufe)
gelangen dadurch nie in ein Paket. Ohne Git-Arbeitsverzeichnis bricht der
Bau ab.

Vor dem Bau laeuft eine Release-Validierung: Pflichtmanifeste
.claude-plugin/plugin.json und .claude-plugin/marketplace.json vorhanden
und gueltiges JSON, Pluginname in beiden Manifesten identisch, Version in
plugin.json synchron zu VERSION in werkzeuge/ja_pruefung.py, SKILL.md mit
Frontmatter vorhanden, Checkzahl-Angaben ("<n> Checks") in README, SKILL.md
und plugin.json gleich len(befunde.KATALOG) (Regel aus CLAUDE.md). Nach dem
Bau wird der Plugin-Archivinhalt geprueft (Pflichteintraege inkl.
PBIP-Vorlage enthalten, Ausschluesse nicht enthalten). Jeder Verstoss
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
import subprocess
import sys
import zipfile
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
DIST = BASIS / "dist"

# Einzige Ausschlussdefinition - gilt fuer Bau UND Archivpruefung.
AUSSCHLUSS_ORDNER = {"__pycache__", "dist", ".git", "JA-Pruefung"}
AUSSCHLUSS_PFADE = [("testdaten", "ausgabe")]  # generierte Prueflaeufe
PLUGIN_WURZELN = {".claude-plugin", "skills", "werkzeuge"}
PLUGIN_WURZELDATEIEN = {"README.md", "LICENSE"}
MANIFEST_PLUGIN = Path(".claude-plugin") / "plugin.json"
MANIFEST_MARKT = Path(".claude-plugin") / "marketplace.json"
SKILL = Path("skills") / "ja-pruefung" / "SKILL.md"
PIPELINE = Path("werkzeuge") / "ja_pruefung.py"
PBI_VORLAGE = Path("werkzeuge") / "pbi_vorlage"
# Vorlage, die ja_pruefung.py --pbi per copytree in jede Ausgabe kopiert:
# ohne sie ist das Plugin funktional unvollstaendig.
PBI_PFLICHT = (
    PBI_VORLAGE / "JA-Pruefbericht.pbip",
    PBI_VORLAGE / "JA-Pruefbericht.Report" / ".platform",
    PBI_VORLAGE / "JA-Pruefbericht.Report" / "definition.pbir",
    PBI_VORLAGE / "JA-Pruefbericht.Report" / "report.json",
    PBI_VORLAGE / "JA-Pruefbericht.SemanticModel" / ".platform",
    PBI_VORLAGE / "JA-Pruefbericht.SemanticModel" / "definition.pbism",
    PBI_VORLAGE / "JA-Pruefbericht.SemanticModel" / "model.bim",
)
ARCHIV_PFLICHT = (MANIFEST_PLUGIN, MANIFEST_MARKT, SKILL, PIPELINE,
                  Path("README.md"), Path("LICENSE"), *PBI_PFLICHT)
# Fundstellen der Checkzahl (CLAUDE.md: folgen len(befunde.KATALOG)).
CHECKZAHL_DATEIEN = (Path("README.md"), SKILL, MANIFEST_PLUGIN)
CHECKZAHL_MUSTER = re.compile(r"(\d+) Checks\b")


def _lies(rel: Path, fehler: list[str]) -> str | None:
    pfad = BASIS / rel
    if not pfad.is_file():
        fehler.append(f"{rel.as_posix()} fehlt")
        return None
    try:
        return pfad.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        fehler.append(f"{rel.as_posix()}: nicht lesbar ({e})")
        return None


def _json_objekt(rel: Path, fehler: list[str]) -> dict | None:
    text = _lies(rel, fehler)
    if text is None:
        fehler[-1] += " (Pflichtdatei der Plugin-Spezifikation)"
        return None
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as e:
        fehler.append(f"{rel.as_posix()}: kein gueltiges JSON ({e})")
        return None
    if not isinstance(daten, dict):
        fehler.append(f"{rel.as_posix()}: JSON-Wurzel muss ein Objekt sein "
                      f"(ist {type(daten).__name__})")
        return None
    return daten


def _katalog_groesse(fehler: list[str]) -> int | None:
    """len(befunde.KATALOG) - Import ohne Seiteneffekte (reine Definitionen)."""
    sys.path.insert(0, str(BASIS / "werkzeuge"))
    try:
        import befunde  # noqa: PLC0415  (Import erst nach sys.path-Setup)
    except Exception as e:  # noqa: BLE001  (jede Importstoerung ist ein Befund)
        fehler.append(f"werkzeuge/befunde.py nicht importierbar: {e}")
        return None
    finally:
        sys.path.pop(0)
    return len(befunde.KATALOG)


def validiere_repo() -> list[str]:
    """Prueft die Plugin-Sollstruktur vor dem Bau; liefert Fehlerliste."""
    fehler: list[str] = []
    plugin = _json_objekt(MANIFEST_PLUGIN, fehler)
    markt = _json_objekt(MANIFEST_MARKT, fehler)

    # Altlast abfangen: endungslose Manifeste blockieren die Installation
    for alt in ("plugin", "marketplace"):
        if (BASIS / ".claude-plugin" / alt).exists():
            fehler.append(f".claude-plugin/{alt}: endungslose Manifestdatei "
                          f"- in {alt}.json umbenennen")

    if plugin is not None:
        for feld in ("name", "version", "description"):
            if not plugin.get(feld):
                fehler.append(f"plugin.json: Feld '{feld}' fehlt oder leer")
        quelle = _lies(PIPELINE, fehler)
        if quelle is not None:
            treffer = re.search(r'^VERSION\s*=\s*"([^"]+)"', quelle, re.M)
            if not treffer:
                fehler.append(f"{PIPELINE.as_posix()}: VERSION-Konstante "
                              "nicht gefunden")
            elif plugin.get("version") != treffer.group(1):
                fehler.append(
                    f"Versionsdrift: plugin.json {plugin.get('version')!r} "
                    f"!= ja_pruefung.py VERSION {treffer.group(1)!r}")

    if plugin is not None and markt is not None:
        eintraege = markt.get("plugins")
        if not isinstance(eintraege, list):
            fehler.append("marketplace.json: 'plugins' fehlt oder ist "
                          "keine Liste")
        else:
            namen = [p.get("name") for p in eintraege if isinstance(p, dict)]
            if plugin.get("name") not in namen:
                fehler.append(
                    f"marketplace.json: Plugin {plugin.get('name')!r} nicht "
                    f"unter 'plugins' gelistet (gefunden: {namen})")

    inhalt = _lies(SKILL, fehler)
    if inhalt is not None:
        if not inhalt.startswith("---") or inhalt.count("---") < 2:
            fehler.append(f"{SKILL.as_posix()}: YAML-Frontmatter "
                          "(--- ... ---) fehlt")
        else:
            frontmatter = inhalt.split("---", 2)[1]
            for feld in ("name:", "description:"):
                if feld not in frontmatter:
                    fehler.append(f"{SKILL.as_posix()}-Frontmatter: "
                                  f"'{feld}' fehlt")

    # Checkzahl-Gate: jede "<n> Checks"-Angabe muss len(befunde.KATALOG) sein
    soll = _katalog_groesse(fehler)
    if soll is not None:
        for rel in CHECKZAHL_DATEIEN:
            text = _lies(rel, fehler)
            if text is None:
                continue
            zahlen = [int(z) for z in CHECKZAHL_MUSTER.findall(text)]
            if not zahlen:
                fehler.append(f"{rel.as_posix()}: keine Checkzahl-Angabe "
                              f"('<n> Checks') gefunden - erwartet {soll}")
            for zahl in zahlen:
                if zahl != soll:
                    fehler.append(
                        f"Checkzahl-Drift: {rel.as_posix()} nennt "
                        f"{zahl} Checks, len(befunde.KATALOG) = {soll}")
    return fehler


def validiere_archiv(ziel: Path) -> list[str]:
    """Prueft den fertigen Plugin-Archivinhalt; liefert Fehlerliste."""
    fehler: list[str] = []
    with zipfile.ZipFile(ziel) as z:
        eintraege = set(z.namelist())
    for pflicht in ARCHIV_PFLICHT:
        if pflicht.as_posix() not in eintraege:
            fehler.append(f"{ziel.name}: Pflichteintrag "
                          f"{pflicht.as_posix()} fehlt")
    verboten = sorted(e for e in eintraege if not _relevant(Path(e)))
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


def versionierte_dateien() -> list[Path]:
    """Alle von Git versionierten Dateien (Index), die im Arbeitsbaum liegen."""
    ergebnis = subprocess.run(
        ["git", "-C", str(BASIS), "ls-files", "-z"],
        capture_output=True, check=True)
    rel = [Path(p) for p in ergebnis.stdout.decode("utf-8").split("\0") if p]
    return [BASIS / r for r in rel if (BASIS / r).is_file() and _relevant(r)]


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
    try:
        alle = versionierte_dateien()
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"FEHLER: Git-Index nicht lesbar ({e}) - der Bau benoetigt "
              "ein Git-Arbeitsverzeichnis.", file=sys.stderr)
        return 1
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
    print("Release-Validierung: Manifeste, Versionsgleichlauf, Checkzahl, "
          "SKILL-Frontmatter und Archivinhalt geprueft - keine Befunde.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
