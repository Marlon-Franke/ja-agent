"""Gibt den CHANGELOG-Abschnitt einer Version aus (Release-Notes fuer
`gh release create --notes-file`, Workflow release.yml).

  py werkzeuge/release_notes.py <version|vVersion> [--pruefe-version]

--pruefe-version: zusaetzlich Abbruch (Exit 1), wenn die Version nicht mit
`version` in .claude-plugin/plugin.json uebereinstimmt (Tag-Gate).
Exit 2, wenn CHANGELOG.md keinen Abschnitt `## [<version>]` enthaelt.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASIS = Path(__file__).resolve().parents[1]
CHANGELOG = BASIS / "CHANGELOG.md"
PLUGIN_MANIFEST = BASIS / ".claude-plugin" / "plugin.json"


def abschnitt(version: str) -> str | None:
    text = CHANGELOG.read_text(encoding="utf-8")
    muster = re.compile(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
                        re.S | re.M)
    treffer = muster.search(text)
    return treffer.group(1).strip() + "\n" if treffer else None


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    version = argv[0].lstrip("v")
    if "--pruefe-version" in argv[1:]:
        soll = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8")).get("version")
        if soll != version:
            print(f"FEHLER: Tag/Version {version!r} != plugin.json {soll!r}",
                  file=sys.stderr)
            return 1
    notizen = abschnitt(version)
    if notizen is None:
        print(f"FEHLER: CHANGELOG.md hat keinen Abschnitt '## [{version}]'",
              file=sys.stderr)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(notizen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
