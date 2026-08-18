"""Kanonischer Release-Check: alle Release-Gates in definierter Reihenfolge,
ein Befehl, ein Exit-Code (Revisionsbefund P1.1). README, .claude/CLAUDE.md
und die CI rufen genau diesen Befehl auf:

  py werkzeuge/release_check.py [--ohne-plugin-cli] [--erlaube-schmutzig]
                                [--streng] [--ausgabe testdaten/ausgabe]

Gates (Abbruch erst am Ende, alle Befunde werden gesammelt):
   1  Umgebung          Python >= 3.10, Laufzeitabhaengigkeiten (abhaengigkeiten.py)
   2  Syntax            compileall werkzeuge/ testdaten/
   3  Sollstruktur      baue_dist.validiere_repo(): Manifeste, Versions-
                        gleichlauf, Checkzahl, SKILL-Frontmatter, Katalog-
                        Doku/-IDs, Referenzstand, CLAUDE.md-Ablage
   4  Testdaten         erzeuge_testdaten.py; versionierte CSVs unveraendert
                        (Generator und Repository-Stand stimmen ueberein)
   5-7 Referenzlaeufe   standard / dq02 / co02 aus testdaten/erwartung.json,
                        Vergleich von befunde.json, llm_kandidaten.json und
                        stdout ueber pruefe_erwartung.vergleiche_lauf
   8  Markdown-Links    relative Links aller versionierten *.md aufloesbar
   9  Plugin-CLI        claude plugin validate --strict fuer plugin.json und
                        marketplace.json (offizielle Validierung; mit
                        --ohne-plugin-cli ausdruecklich uebersprungen)
  10  Distributionsbau  baue_dist.py (reproduzierbare Archive, Archivinhalt,
                        SHA256SUMS.txt)
  11  Zusatzscans       ruff (Codequalitaet) und pip-audit (bekannte
                        Schwachstellen), sofern installiert (requirements-
                        dev.txt); --streng verlangt sie
Exit 0 = alle Gates bestanden, 1 = mindestens ein Gate verletzt.
Sicherheits-/Lizenz-Scans der Abhaengigkeiten laufen zusaetzlich im
CI-Job `security` (docs/test-strategy.md).
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
WERKZEUGE = BASIS / "werkzeuge"
sys.path.insert(0, str(WERKZEUGE))

import abhaengigkeiten  # noqa: E402
import baue_dist  # noqa: E402
import pruefe_erwartung  # noqa: E402

MIN_PYTHON = (3, 10)
LINK_MUSTER = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LAEUFE = (("standard", Path()), ("dq02", Path("dq02")), ("co02", Path("co02")))


class Bericht:
    def __init__(self) -> None:
        self.fehler: list[str] = []
        self.schritt = 0

    def gate(self, titel: str) -> None:
        self.schritt += 1
        print(f"\n[{self.schritt:2d}] {titel}")

    def ok(self, text: str) -> None:
        print(f"     OK   {text}")

    def fehl(self, text: str) -> None:
        self.fehler.append(text)
        print(f"     FEHLER {text}")

    def uebersprungen(self, text: str) -> None:
        print(f"     --   {text}")


def _lauf(befehl: list[str], cwd: Path = BASIS,
          umgebung: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if umgebung:
        env.update(umgebung)
    return subprocess.run(befehl, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, check=False)


def _versionierte_md() -> list[Path]:
    roh = subprocess.run(["git", "-C", str(BASIS), "ls-files", "-z", "*.md", "**/*.md"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    return [BASIS / p for p in roh.split("\0") if p]


def pruefe_links(b: Bericht) -> None:
    b.gate("Markdown-Links (relative Verweise aller versionierten *.md)")
    try:
        dateien = _versionierte_md()
    except (OSError, subprocess.CalledProcessError) as e:
        b.fehl(f"git ls-files nicht ausfuehrbar ({e})")
        return
    defekt = 0
    for md in dateien:
        text = md.read_text(encoding="utf-8", errors="replace")
        # Codebloecke ausklammern (Beispiel-Links, Platzhalter)
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for ziel in LINK_MUSTER.findall(text):
            if re.match(r"^(https?:|mailto:|#|<)", ziel):
                continue
            pfad = ziel.split("#", 1)[0]
            if not pfad:
                continue
            pfad = pfad.replace("%20", " ").replace("%C3%BC", "ü")
            kandidat = (md.parent / pfad).resolve()
            if not kandidat.exists():
                defekt += 1
                b.fehl(f"{md.relative_to(BASIS).as_posix()}: Link-Ziel fehlt: {ziel}")
    if not defekt:
        b.ok(f"{len(dateien)} Markdown-Dateien, alle relativen Links aufloesbar")


def pruefe_plugin_cli(b: Bericht, ueberspringen: bool) -> None:
    b.gate("Offizielle Plugin-Validierung (claude plugin validate --strict)")
    if ueberspringen:
        b.uebersprungen("mit --ohne-plugin-cli ausdruecklich uebersprungen "
                        "(CI-Job release-check fuehrt sie aus)")
        return
    cli = shutil.which("claude")
    if not cli:
        b.fehl("Claude-Code-CLI 'claude' nicht im PATH - installieren "
               "(https://code.claude.com/docs/en/setup) oder --ohne-plugin-cli")
        return
    for ziel in (".claude-plugin/plugin.json", "."):
        erg = _lauf([cli, "plugin", "validate", ziel, "--strict"])
        ausgabe = (erg.stdout + erg.stderr).strip().splitlines()
        if erg.returncode != 0:
            b.fehl(f"claude plugin validate {ziel} --strict: Exit {erg.returncode}: "
                   + " | ".join(z.strip() for z in ausgabe if z.strip())[:600])
        else:
            b.ok(f"validate {ziel} --strict bestanden")


def pruefe_zusatzscans(b: Bericht, streng: bool) -> None:
    b.gate("Zusatzscans: ruff (Codequalitaet), pip-audit (Schwachstellen)")
    for modul, befehl, titel in (
            ("ruff", [sys.executable, "-m", "ruff", "check", "werkzeuge", "testdaten"],
             "ruff check werkzeuge testdaten"),
            ("pip_audit", [sys.executable, "-m", "pip_audit", "-r",
                           str(BASIS / "requirements.txt"), "--strict",
                           "--progress-spinner", "off"],
             "pip-audit -r requirements.txt")):
        if importlib.util.find_spec(modul) is None:
            if streng:
                b.fehl(f"{titel}: Werkzeug nicht installiert "
                       "(python -m pip install -r requirements-dev.txt)")
            else:
                b.uebersprungen(f"{titel}: nicht installiert (requirements-dev.txt); "
                                "--streng verlangt den Scan")
            continue
        erg = _lauf(befehl)
        if erg.returncode != 0:
            b.fehl(f"{titel}: Exit {erg.returncode}\n"
                   + (erg.stdout + erg.stderr).strip()[-1500:])
        else:
            b.ok(f"{titel}: keine Befunde")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--ohne-plugin-cli", action="store_true",
                   help="claude plugin validate ueberspringen (Matrix-Jobs ohne CLI)")
    p.add_argument("--erlaube-schmutzig", action="store_true",
                   help="Distributionsbau trotz uncommitteter Aenderungen "
                        "(Archive enthalten dann den Commit-Stand)")
    p.add_argument("--streng", action="store_true",
                   help="ruff und pip-audit muessen installiert sein und laufen")
    p.add_argument("--ausgabe", type=Path, default=BASIS / "testdaten" / "ausgabe",
                   help="Ausgabeordner der Referenzlaeufe (Standard testdaten/ausgabe)")
    args = p.parse_args(argv)
    for strom in (sys.stdout, sys.stderr):  # Windows-Konsole (cp1252): nie abbrechen
        if hasattr(strom, "reconfigure"):
            strom.reconfigure(errors="replace")
    b = Bericht()
    print(f"JA-Agent Release-Check | Python {sys.version.split()[0]} | {BASIS}")

    # 1 Umgebung
    b.gate("Umgebung: Python-Version und Laufzeitabhaengigkeiten")
    if sys.version_info < MIN_PYTHON:
        b.fehl(f"Python {sys.version.split()[0]} < {'.'.join(map(str, MIN_PYTHON))}")
    else:
        b.ok(f"Python {sys.version.split()[0]}")
    fehlend = abhaengigkeiten.fehlende_pakete()
    if fehlend:
        b.fehl(abhaengigkeiten.installationshinweis(fehlend))
    else:
        b.ok("Laufzeitabhaengigkeiten vorhanden: " + ", ".join(abhaengigkeiten.PAKETE))

    # 2 Syntax
    b.gate("Syntax: compileall werkzeuge/ testdaten/")
    erg = _lauf([sys.executable, "-m", "compileall", "-q", "werkzeuge", "testdaten"])
    if erg.returncode != 0:
        b.fehl("compileall: " + (erg.stdout + erg.stderr).strip()[-1500:])
    else:
        b.ok("alle Module kompilierbar")

    # 3 Sollstruktur
    b.gate("Sollstruktur: Manifeste, Version, Checkzahl, Katalog-Doku, Referenzstand")
    strukturfehler = baue_dist.validiere_repo()
    for f in strukturfehler:
        b.fehl(f)
    if not strukturfehler:
        b.ok("Plugin-Sollstruktur, Katalog-Doku und Referenzstand konsistent")

    # 4 Testdaten
    b.gate("Testdaten: Generator laeuft, versionierte CSVs unveraendert")
    erg = _lauf([sys.executable, str(BASIS / "testdaten" / "erzeuge_testdaten.py")])
    if erg.returncode != 0:
        b.fehl("erzeuge_testdaten.py: " + (erg.stdout + erg.stderr).strip()[-1500:])
    else:
        diff = subprocess.run(["git", "-C", str(BASIS), "status", "--porcelain",
                               "--untracked-files=no", "--", "testdaten"],
                              capture_output=True, text=True, check=False)
        geaendert = [z[3:] for z in diff.stdout.splitlines()
                     if z.strip() and z[3:].lower().endswith(".csv")]
        if diff.returncode != 0:
            b.fehl("git status testdaten nicht ausfuehrbar")
        elif geaendert:
            b.fehl("Generator erzeugt andere CSVs als versioniert: "
                   + ", ".join(geaendert) + " - Testdaten committen oder Generator pruefen")
        else:
            b.ok(erg.stdout.strip().splitlines()[0] if erg.stdout.strip() else "generiert")

    # 5-7 Referenzlaeufe
    erwartung = pruefe_erwartung.lade_erwartung()
    for name, unterordner in LAEUFE:
        lauf = pruefe_erwartung.effektiver_lauf(erwartung, name)
        b.gate(f"Referenzlauf '{name}': {lauf.get('beschreibung', '')}")
        ziel = args.ausgabe / unterordner
        erg = _lauf([sys.executable, str(WERKZEUGE / "ja_pruefung.py"),
                     *lauf["argumente"], "--ausgabe", str(ziel)])
        protokoll = erg.stdout + erg.stderr
        if erg.returncode != 0:
            b.fehl(f"ja_pruefung.py Exit {erg.returncode}: {protokoll.strip()[-1500:]}")
            continue
        abweichungen = pruefe_erwartung.vergleiche_lauf(name, ziel, protokoll, erwartung)
        for a in abweichungen:
            b.fehl(a)
        if not abweichungen:
            b.ok(f"{len(lauf['checks'])} Checks wie erwartet, Summen {lauf['summen']}, "
                 f"KI-Kandidaten {lauf['ki_kandidaten']}, keine Bilanzprobe-Warnung")

    # 8 Links
    pruefe_links(b)

    # 9 Plugin-CLI
    pruefe_plugin_cli(b, args.ohne_plugin_cli)

    # 10 Distributionsbau
    b.gate("Distributionsbau: baue_dist.py (reproduzierbar, Archivinhalt, SHA256SUMS)")
    bau_argv = ["--erlaube-schmutzig"] if args.erlaube_schmutzig else []
    erg = _lauf([sys.executable, str(WERKZEUGE / "baue_dist.py"), *bau_argv])
    if erg.returncode != 0:
        b.fehl("baue_dist.py: " + (erg.stdout + erg.stderr).strip()[-1500:])
    else:
        for zeile in erg.stdout.strip().splitlines():
            if zeile.startswith(("gebaut:", "Quelle:")):
                b.ok(zeile)
        if erg.stderr.strip():
            b.ok("Hinweis: " + erg.stderr.strip().splitlines()[0][:200])

    # 11 Zusatzscans
    pruefe_zusatzscans(b, args.streng)

    print()
    if b.fehler:
        print(f"RELEASE-CHECK NICHT BESTANDEN: {len(b.fehler)} Befund(e).",
              file=sys.stderr)
        for f in b.fehler:
            print(f"  - {f.splitlines()[0][:300]}", file=sys.stderr)
        return 1
    print("RELEASE-CHECK BESTANDEN: alle Gates gruen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
