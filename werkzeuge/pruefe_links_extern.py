"""Periodischer, toleranter Linkcheck der EXTERNEN Verweise aller versionierten
Markdown-Dateien (Revisionspruefung v0.4.4, Befund P2.3). Relative Links
prueft release_check.py als Release-Gate; externe Links (DATEV, Gesetze,
Claude-Code-/GitHub-Doku) altern unbemerkt - dieser Check meldet das
regelmaessig (Workflow linkcheck.yml: monatlich + manuell), blockiert aber
keinen Pull Request.

  py werkzeuge/pruefe_links_extern.py [--zeitlimit 30] [--versuche 3]
                                      [--parallel 8] [--zeige-ok]

Toleranz: 2xx/3xx = erreichbar; 401/403/405/429 = erreichbar, aber
anmelde-/bot-geschuetzt oder limitiert (Hinweis, kein Fehler); Domains in
AUSNAHMEN (Anmeldepflicht/Bot-Schutz, dokumentierter Grund) werden
uebersprungen. Defekt = 404/410 oder nach allen Versuchen 5xx/Netzfehler.
Exit 0 = keine defekten Links, 1 = defekte Links, 2 = Aufruffehler.
Nur Standardbibliothek.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
LINK_MUSTER = re.compile(
    r"(?<!!)\[[^\]]*\]\((https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)|<(https?://[^>\s]+)>")
# Domain -> Grund (uebersprungen): Single-Page-Anwendungen, die auch fuer nicht
# existierende Dokument-IDs HTTP 200 liefern - ein HTTP-Check kann dort die
# Existenz des Dokuments nicht belegen; Pruefung nur manuell
# (docs/test-strategy.md, Abschnitt "Manuelle Release-Checkliste").
AUSNAHMEN: dict[str, str] = {
    "developer.datev.de": "DATEV Developer-Portal (SPA, immer 200; Details nach Anmeldung)",
    "help-center.apps.datev.de": "DATEV Hilfe-Center (SPA, immer 200)",
    "wissensplattform.apps.datev.de": "DATEV Wissensplattform (SPA, immer 200)",
}
GEDULDET = {401, 403, 405, 429}  # erreichbar, aber geschuetzt/limitiert
UA = ("Mozilla/5.0 (compatible; ja-agent-linkcheck/1.0; "
      "+https://github.com/Marlon-Franke/ja-agent)")


def versionierte_md() -> list[Path]:
    roh = subprocess.run(["git", "-C", str(BASIS), "ls-files", "-z", "*.md", "**/*.md"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    return [BASIS / p for p in roh.split("\0") if p]


def links_aus(md: Path) -> set[str]:
    text = re.sub(r"```.*?```", "",
                  md.read_text(encoding="utf-8", errors="replace"), flags=re.S)
    return {(a or b).rstrip(".,;:") for a, b in LINK_MUSTER.findall(text)}


def _domain(url: str) -> str:
    return url.split("/", 3)[2].lower()


def pruefe(url: str, zeitlimit: float, versuche: int) -> tuple[int | None, str]:
    """(HTTP-Status oder None, Meldung) - GET mit Wiederholung/Backoff
    (HEAD lehnen viele Server ab)."""
    letzte = ""
    for versuch in range(1, versuche + 1):
        anfrage = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        try:
            with urllib.request.urlopen(anfrage, timeout=zeitlimit) as antwort:
                return antwort.status, "ok"
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return e.code, f"HTTP {e.code}"
            if e.code < 500 and e.code != 408:
                return e.code, f"HTTP {e.code}"
            letzte = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            letzte = f"{type(e).__name__}: {e}"
        time.sleep(min(2.0 * versuch, 6.0))
    return None, letzte or "unbekannt"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--zeitlimit", type=float, default=30.0)
    p.add_argument("--versuche", type=int, default=3)
    p.add_argument("--parallel", type=int, default=8)
    p.add_argument("--zeige-ok", action="store_true")
    args = p.parse_args(argv)
    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, "reconfigure"):
            strom.reconfigure(errors="replace")
    try:
        dateien = versionierte_md()
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"FEHLER: git ls-files nicht ausfuehrbar ({e})", file=sys.stderr)
        return 2
    fundstellen: dict[str, set[str]] = {}
    for md in dateien:
        for url in links_aus(md):
            fundstellen.setdefault(url, set()).add(md.relative_to(BASIS).as_posix())
    uebersprungen = [u for u in fundstellen if _domain(u) in AUSNAHMEN]
    zu_pruefen = sorted(u for u in fundstellen if _domain(u) not in AUSNAHMEN)
    print(f"{len(fundstellen)} externe Links in {len(dateien)} Markdown-Dateien; "
          f"{len(uebersprungen)} uebersprungen (Ausnahmen), {len(zu_pruefen)} geprueft")
    for domain, grund in AUSNAHMEN.items():
        n = sum(1 for u in uebersprungen if _domain(u) == domain)
        if n:
            print(f"  Ausnahme {domain} ({n}): {grund}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
        ergebnisse = dict(zip(zu_pruefen, pool.map(
            lambda u: pruefe(u, args.zeitlimit, args.versuche), zu_pruefen)))
    defekt: list[str] = []
    hinweise: list[str] = []
    for url in zu_pruefen:
        status, meldung = ergebnisse[url]
        wo = ", ".join(sorted(fundstellen[url]))
        if status is not None and 200 <= status < 400:
            if args.zeige_ok:
                print(f"  OK      {status} {url}")
        elif status in GEDULDET:
            hinweise.append(f"  HINWEIS {meldung} (geschuetzt/limitiert): {url}  [{wo}]")
        else:
            defekt.append(f"  DEFEKT  {meldung}: {url}  [{wo}]")
    for z in hinweise:
        print(z)
    for z in defekt:
        print(z, file=sys.stderr)
    print(f"Ergebnis: {len(defekt)} defekt, {len(hinweise)} geschuetzt/limitiert, "
          f"{len(zu_pruefen) - len(defekt) - len(hinweise)} erreichbar")
    return 1 if defekt else 0


if __name__ == "__main__":
    raise SystemExit(main())
