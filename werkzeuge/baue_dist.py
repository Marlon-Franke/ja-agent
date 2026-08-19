"""Baut die Distributionspakete in dist/ reproduzierbar aus einem Git-Commit.

  py werkzeuge/baue_dist.py [--ref HEAD] [--erlaube-schmutzig]

Erzeugt:
  dist/jahresabschluss-agent_GitHub.zip  Repo-Abbild (alle im Commit
                                         versionierten Dateien)
  dist/jahresabschluss-agent.plugin      Plugin-Paket (.claude-plugin,
                                         skills, werkzeuge, README, LICENSE,
                                         requirements.txt)
  dist/SHA256SUMS.txt                    Pruefsummen beider Archive
                                         (Format `sha256sum -c`)

Reproduzierbarkeit (Revisionsbefund P2.3): Dateiliste UND Inhalte kommen
aus dem Git-Objektspeicher des Commits (`git ls-tree`, `git cat-file`),
nicht aus dem Arbeitsbaum - uncommittete Aenderungen, ungetrackte
Streudateien und plattformabhaengige Zeilenenden des Checkouts gelangen
nie in ein Paket. Alle ZIP-Eintraege tragen den Commit-Zeitstempel, feste
Unix-Rechte (0644) und werden unkomprimiert (ZIP_STORED) geschrieben,
weil Deflate-Streams zwischen zlib-Varianten (zlib, zlib-ng) abweichen.
Damit ergibt derselbe Commit auf jeder Plattform und jeder unterstuetzten
Python-Version byteidentische Archive; die CI vergleicht die Pruefsummen
ueber die Matrix (docs/test-strategy.md), das Release-Workflow baut aus
dem Tag. Standardmaessig bricht der Bau ab, wenn versionierte Dateien im
Arbeitsbaum uncommittete Aenderungen tragen (sie waeren nicht im Paket);
`--erlaube-schmutzig` baut trotzdem aus dem Commit.

Vor dem Bau laeuft eine Release-Validierung: Pflichtmanifeste
.claude-plugin/plugin.json und .claude-plugin/marketplace.json vorhanden
und gueltiges JSON, Pluginname in beiden Manifesten identisch, Version in
plugin.json synchron zu VERSION in werkzeuge/ja_pruefung.py, SKILL.md mit
Frontmatter vorhanden, Checkzahl-Angaben ("<n> Checks") in README, SKILL.md
und plugin.json gleich len(befunde.KATALOG) (Regel aus .claude/CLAUDE.md),
generierte Doku-Bloecke aktuell und kanonischer Soll-Katalog
(werkzeuge/soll_katalog.json) konsistent zu befunde.KATALOG und
Referenzkatalog (katalog_doku.pruefe). Nach dem Bau wird der Plugin-Archivinhalt
geprueft (Pflichteintraege inkl. PBIP-Vorlage und requirements.txt
enthalten, Ausschluesse nicht enthalten). Jeder Verstoss bricht mit
Exit-Code 1 ab - ein erfolgreicher Build garantiert damit die Sollstruktur
der Claude-Code-Plugin-Spezifikation
(https://code.claude.com/docs/en/plugins-reference).

Grund fuer dieses Skript statt Compress-Archive (Windows PowerShell 5.1):
ZIP-Eintraege muessen Forward-Slashes als Pfadtrenner tragen (PKWARE
APPNOTE 4.4.17.1, https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT);
Python zipfile schreibt sie so und setzt fuer Nicht-ASCII-Dateinamen das
UTF-8-Flag - Compress-Archive tut beides nicht (Backslash-Eintraege,
OEM-kodierte Umlaute, entpackt unter Linux/macOS fehlerhaft).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
DIST = BASIS / "dist"

# Einzige Ausschlussdefinition - gilt fuer Bau UND Archivpruefung.
AUSSCHLUSS_ORDNER = {"__pycache__", "dist", ".git", "JA-Pruefung"}
AUSSCHLUSS_PFADE = [("testdaten", "ausgabe")]  # generierte Prueflaeufe
PLUGIN_WURZELN = {".claude-plugin", "skills", "werkzeuge"}
PLUGIN_WURZELDATEIEN = {"README.md", "LICENSE", "requirements.txt"}
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
# requirements.txt ist Pflicht (Revisionsbefund P0.1): die Plugin-
# Installation installiert keine Python-Pakete, der Skill verweist auf
# ${CLAUDE_PLUGIN_ROOT}/requirements.txt.
ARCHIV_PFLICHT = (MANIFEST_PLUGIN, MANIFEST_MARKT, SKILL, PIPELINE,
                  Path("werkzeuge") / "abhaengigkeiten.py",
                  Path("README.md"), Path("LICENSE"), Path("requirements.txt"),
                  *PBI_PFLICHT)
# Fundstellen der Checkzahl (CLAUDE.md: folgen len(befunde.KATALOG)).
CHECKZAHL_DATEIEN = (Path("README.md"), SKILL, MANIFEST_PLUGIN)
CHECKZAHL_MUSTER = re.compile(r"(\d+) Checks\b")
ARCHIV_GITHUB = "jahresabschluss-agent_GitHub.zip"
ARCHIV_PLUGIN = "jahresabschluss-agent.plugin"
PRUEFSUMMEN = "SHA256SUMS.txt"


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
    # CLAUDE.md an der Plugin-Wurzel = Warnung von `claude plugin validate
    # --strict` (wird nicht als Plugin-Kontext geladen); Projektanweisungen
    # liegen deshalb in .claude/CLAUDE.md (https://code.claude.com/docs/en/memory).
    if (BASIS / "CLAUDE.md").exists():
        fehler.append("CLAUDE.md an der Plugin-Wurzel: nach .claude/CLAUDE.md "
                      "verschieben (strict-Validierung der Plugin-Spezifikation)")

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

    # Katalog-Doku-Gate: generierte Bloecke aktuell (README-Pruefkatalog,
    # Abdeckungsmatrix, Ebenen-Tabelle, Check-Register, Referenzstand),
    # kanonischer Soll-Katalog werkzeuge/soll_katalog.json konsistent zu
    # befunde.KATALOG und Referenzkatalog (katalog_doku.pruefe)
    sys.path.insert(0, str(BASIS / "werkzeuge"))
    try:
        import katalog_doku  # noqa: PLC0415
        fehler.extend(katalog_doku.pruefe())
    except Exception as e:  # noqa: BLE001
        fehler.append(f"werkzeuge/katalog_doku.py nicht ausfuehrbar: {e}")
    finally:
        sys.path.pop(0)

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
        defekt = z.testzip()
    if defekt:
        fehler.append(f"{ziel.name}: CRC-Fehler bei {defekt}")
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


def _git(*args: str, eingabe: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(BASIS), *args], input=eingabe,
                          capture_output=True, check=True).stdout


def commit_info(ref: str) -> tuple[str, datetime]:
    """(Commit-SHA, Commit-Zeit UTC) des Bezugscommits."""
    zeile = _git("log", "-1", "--format=%H %ct", ref).decode().split()
    return zeile[0], datetime.fromtimestamp(int(zeile[1]), tz=timezone.utc)


def versionierte_dateien(ref: str) -> list[Path]:
    """Alle im Commit versionierten Dateien (relativ), Ausschluesse gefiltert,
    plattformunabhaengig sortiert (nach POSIX-Pfadstring, Codepoint-Ordnung -
    Path-Objekte sortieren unter Windows case-insensitiv und wuerden die
    Archivreihenfolge und damit die Pruefsumme plattformabhaengig machen)."""
    roh = _git("ls-tree", "-r", "-z", "--name-only", ref).decode("utf-8")
    dateien = [Path(p) for p in roh.split("\0") if p and _relevant(Path(p))]
    return sorted(dateien, key=lambda p: p.as_posix())


def blob_inhalte(ref: str, dateien: list[Path]) -> dict[Path, bytes]:
    """Dateiinhalte aus dem Objektspeicher (git cat-file --batch, ein Prozess);
    roh, ohne Zeilenende-Konvertierung des Arbeitsbaums."""
    anfrage = "".join(f"{ref}:{p.as_posix()}\n" for p in dateien).encode("utf-8")
    roh = _git("cat-file", "--batch", eingabe=anfrage)
    inhalte: dict[Path, bytes] = {}
    pos = 0
    for datei in dateien:
        ende = roh.index(b"\n", pos)
        kopf = roh[pos:ende].decode("utf-8").split()
        if len(kopf) != 3 or kopf[1] != "blob":
            raise RuntimeError(f"git cat-file: {datei.as_posix()} in {ref}: {kopf}")
        laenge = int(kopf[2])
        inhalte[datei] = roh[ende + 1: ende + 1 + laenge]
        pos = ende + 1 + laenge + 1  # abschliessendes \n je Objekt
    return inhalte


def schmutzige_dateien() -> list[str]:
    """Versionierte Dateien mit uncommitteten Aenderungen (Index/Arbeitsbaum)."""
    roh = _git("status", "--porcelain", "--untracked-files=no", "-z").decode("utf-8")
    eintraege = [e for e in roh.split("\0") if e]
    dateien: list[str] = []
    ueberspringe = False
    for eintrag in eintraege:
        if ueberspringe:  # zweiter Eintrag einer Umbenennung/Kopie (Altpfad)
            ueberspringe = False
            continue
        status, pfad = eintrag[:2], eintrag[3:]
        dateien.append(pfad)
        ueberspringe = "R" in status or "C" in status
    return dateien


def _schreibe(ziel: Path, dateien: list[Path], inhalte: dict[Path, bytes],
              zeit: datetime) -> str:
    """Schreibt das Archiv deterministisch; liefert die SHA-256-Pruefsumme."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    stempel = (zeit.year, zeit.month, zeit.day, zeit.hour, zeit.minute, zeit.second)
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_STORED) as z:
        for datei in dateien:
            info = zipfile.ZipInfo(datei.as_posix(), date_time=stempel)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3            # Unix, plattformunabhaengig
            info.external_attr = 0o100644 << 16  # regulaere Datei rw-r--r--
            z.writestr(info, inhalte[datei])
    summe = hashlib.sha256(ziel.read_bytes()).hexdigest()
    groesse = f"{ziel.stat().st_size:,}".replace(",", ".")
    print(f"gebaut: {ziel.name} ({len(dateien)} Dateien, {groesse} Bytes) "
          f"sha256 {summe}")
    return summe


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--ref", default="HEAD",
                   help="Git-Commit/Tag, aus dem gebaut wird (Standard HEAD)")
    p.add_argument("--erlaube-schmutzig", action="store_true",
                   help="trotz uncommitteter Aenderungen an versionierten "
                        "Dateien bauen (Paket enthaelt dann den Commit-Stand, "
                        "nicht den Arbeitsbaum)")
    args = p.parse_args(argv)

    fehler = validiere_repo()
    if fehler:
        for f in fehler:
            print(f"FEHLER: {f}", file=sys.stderr)
        print("Build abgebrochen - Sollstruktur zuerst herstellen.",
              file=sys.stderr)
        return 1
    try:
        sha, zeit = commit_info(args.ref)
        schmutzig = schmutzige_dateien() if args.ref == "HEAD" else []
        alle = versionierte_dateien(args.ref)
        inhalte = blob_inhalte(args.ref, alle)
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as e:
        print(f"FEHLER: Git-Objektspeicher nicht lesbar ({e}) - der Bau "
              "benoetigt ein Git-Arbeitsverzeichnis mit dem Bezugscommit.",
              file=sys.stderr)
        return 1
    if schmutzig:
        meldung = ("versionierte Dateien mit uncommitteten Aenderungen "
                   "(nicht im Paket): " + ", ".join(sorted(schmutzig)[:8])
                   + (" ..." if len(schmutzig) > 8 else ""))
        if not args.erlaube_schmutzig:
            print(f"FEHLER: {meldung}\nZuerst committen oder mit "
                  "--erlaube-schmutzig aus dem Commit-Stand bauen.",
                  file=sys.stderr)
            return 1
        print(f"WARNUNG: {meldung}", file=sys.stderr)
    print(f"Quelle: {args.ref} = {sha[:12]} ({zeit:%Y-%m-%d %H:%M:%S} UTC), "
          f"{len(alle)} versionierte Dateien")

    summen = {ARCHIV_GITHUB: _schreibe(DIST / ARCHIV_GITHUB, alle, inhalte, zeit)}
    plugin = [q for q in alle
              if q.parts[0] in PLUGIN_WURZELN
              or (len(q.parts) == 1 and q.name in PLUGIN_WURZELDATEIEN)]
    ziel = DIST / ARCHIV_PLUGIN
    summen[ARCHIV_PLUGIN] = _schreibe(ziel, plugin, inhalte, zeit)
    fehler = validiere_archiv(ziel)
    if fehler:
        for f in fehler:
            print(f"FEHLER: {f}", file=sys.stderr)
        return 1
    (DIST / PRUEFSUMMEN).write_text(
        "".join(f"{summen[n]}  {n}\n" for n in (ARCHIV_PLUGIN, ARCHIV_GITHUB)),
        encoding="ascii", newline="\n")
    print(f"geschrieben: {PRUEFSUMMEN} (sha256sum -c kompatibel)")
    print("Release-Validierung: Manifeste, Versionsgleichlauf, Checkzahl, "
          "SKILL-Frontmatter, Katalog-Doku/-IDs, Referenzstand und "
          "Archivinhalt geprueft - keine Befunde.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
