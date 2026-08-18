# Teststrategie, Kompatibilitäts- und Supportzusagen

Stand: Release 0.4.4 (2026-08-18). Diese Datei ist die verbindliche
Beschreibung dessen, was vor einem Release automatisch geprüft wird, auf
welchen Plattformen das Plugin unterstützt wird und was ausdrücklich
**nicht** zugesagt ist. Sie beantwortet die Befunde P0.2, P1.1, P1.2,
P1.4, P2.2 und P2.3 der Revisionsprüfung v0.4.3.

## 1. Kanonischer Release-Check

`py werkzeuge/release_check.py` ist der **einzige** Einstieg für alle
Release-Gates – identisch aufgerufen von Entwicklern (README,
`.claude/CLAUDE.md`) und von der CI. Reihenfolge und Inhalt der Gates
stehen im Modul-Docstring; Kurzfassung:

| # | Gate | Quelle der Wahrheit |
|---|---|---|
| 1 | Python ≥ 3.10, Laufzeitabhängigkeiten vorhanden | `werkzeuge/abhaengigkeiten.py`, `requirements.txt` |
| 2 | Syntax (`compileall werkzeuge testdaten`) | – |
| 3 | Plugin-Sollstruktur: Manifeste, Versionsgleichlauf, Checkzahl, SKILL-Frontmatter, generierte Doku-Blöcke, Katalog-IDs README ↔ Matrix ↔ `befunde.KATALOG`, Referenzstand, `CLAUDE.md`-Ablage | `werkzeuge/baue_dist.py`, `werkzeuge/katalog_doku.py` |
| 4 | Testdaten-Generator läuft; erzeugte CSVs == versionierte CSVs | `testdaten/erzeuge_testdaten.py` |
| 5–7 | Referenzläufe `standard`, `dq02`, `co02`: alle 73 Checks je Lauf (Status aktiv/skip, Treffer je Schwere, Belege gesäter Fälle, Skip-Gründe), Summen, KI-Kandidaten, stdout-Kopf/Summenzeile, keine Bilanzprobe-Warnung | `testdaten/erwartung.json` (+ Prosa `erwartung.md`), `werkzeuge/pruefe_erwartung.py` |
| 8 | Relative Markdown-Links aller versionierten `*.md` auflösbar | – |
| 9 | `claude plugin validate --strict` für `plugin.json` **und** `marketplace.json` | Claude-Code-CLI (Referenzversion s. u.); `--ohne-plugin-cli` überspringt ausdrücklich |
| 10 | Reproduzierbarer Distributionsbau, Archivinhalt, `SHA256SUMS.txt` | `werkzeuge/baue_dist.py` |
| 11 | `ruff check` (Regelsatz `ruff.toml`), `pip-audit -r requirements.txt` | `requirements-dev.txt`; `--streng` verlangt beide (CI) |

Exit 0 = alle Gates bestanden; 1 = mindestens ein Befund (Liste am Ende).
Erwartungsbilder ändern heißt `erwartung.json` **und** `erwartung.md` im
selben Arbeitsgang nachziehen; die JSON-Datei ist maschinell vollständig
(jede `befunde.KATALOG`-ID muss je Lauf eine Erwartung haben – auch
Nullbefunde sind damit explizit).

## 2. CI (`.github/workflows/ci.yml`)

| Job | Läuft auf | Inhalt |
|---|---|---|
| `release-check` | ubuntu-latest, Python 3.12, Claude-Code-CLI gepinnt | `release_check.py --streng` (alle Gates inkl. offizieller Plugin-Validierung); Artefakte `dist/` als Workflow-Artefakt |
| `marketplace` | ubuntu-latest, Claude-Code-CLI gepinnt | vollständiger lokaler Marketplace-Lebenszyklus mit isoliertem `CLAUDE_CONFIG_DIR`: `marketplace add <Repo>`, `install`, `list --json` (Version == `plugin.json`), `details`, `update`, `uninstall`, `marketplace remove` |
| `paket` | ubuntu-latest | entpacktes `dist/jahresabschluss-agent.plugin` in **frischer** virtueller Umgebung: ohne `openpyxl` → `--help` funktioniert, Pipeline meldet Exit 2 mit Installationshinweis; nach `pip install -r <Paket>/requirements.txt` → Standardlauf über den Paketpfad gegen `erwartung.json` |
| `matrix` | ubuntu/windows/macos × Python 3.10/3.11/3.12/3.13/3.14 | `release_check.py --ohne-plugin-cli --streng`; lädt `dist/SHA256SUMS.txt` je Zelle hoch |
| `reproduzierbarkeit` | ubuntu-latest | vergleicht die `SHA256SUMS.txt` aller Matrix-Zellen und des `release-check`-Jobs – jede Abweichung ist ein Fehler (Beweis der plattform- und versionsunabhängigen Reproduzierbarkeit) |
| `security` | ubuntu-latest | Secret-Scan des Repos (gitleaks), Lizenzprüfung der Laufzeitabhängigkeiten (`pip-licenses`, erlaubt: MIT/BSD/Apache-2.0/PSF/ISC) |

`main` erhält Pushes nur über Pull Requests; die empfohlene GitHub-Absicherung
(Ruleset: PR erforderlich, Status-Checks `CI / release-check`,
`CI / marketplace`, `CI / paket`, `CI / reproduzierbarkeit`, `CI / security`
erforderlich, kein Direkt-Push, lineare Historie) ist eine
Repository-Einstellung und muss vom Repository-Eigentümer gesetzt werden
(siehe [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)).

## 3. Release-Workflow (`.github/workflows/release.yml`)

Auslöser: Push eines annotierten Tags `v<major>.<minor>.<patch>`. Schritte:
Tag == `version` in `plugin.json` (sonst Abbruch), `release_check.py
--streng` mit Claude-CLI, Distributionsbau **aus dem Tag** (Inhalte aus dem
Git-Objektspeicher, Commit-Zeitstempel, `ZIP_STORED` → byteidentisch
reproduzierbar), Release-Notes = CHANGELOG-Abschnitt der Version
(`werkzeuge/release_notes.py`), Veröffentlichung mit `gh release create`
inkl. `jahresabschluss-agent.plugin`, `jahresabschluss-agent_GitHub.zip`,
`SHA256SUMS.txt`. Jeder kann die Prüfsummen lokal nachvollziehen:
`git checkout v<version> && py werkzeuge/baue_dist.py` liefert dieselben
Werte.

## 4. Kompatibilitätsmatrix und Support

| Komponente | Unterstützt (getestet) | Hinweis |
|---|---|---|
| Python | 3.10, 3.11, 3.12, 3.13, 3.14 (CPython) | ältere Versionen: `abhaengigkeiten`/`release_check` melden `< 3.10` als Fehler |
| Betriebssystem | Windows 10/11, Ubuntu (aktuelle LTS), macOS (aktuell) | jeweils die GitHub-Actions-Runner-Images `-latest`; Befehle im README mit `py` (Windows) bzw. `python3` |
| `openpyxl` | `>=3.1,<4` | Obergrenze bewusst: neue Major-Version erst nach Matrixlauf freigeben |
| Claude Code CLI | Referenzversion **2.1.201** (in CI gepinnt: `npm install -g @anthropic-ai/claude-code@<Version>`) | neuere Versionen werden mit dem Pin-Update in `ci.yml` freigegeben; ältere ungetestet |
| Claude Desktop / Cowork | Plugin-Import über `.plugin`-Datei | funktional identisch zum CLI-Paket (gleiches Archiv) |
| DATEV-Format | EXTF/DTVF Version 700, Kategorien 21 (Buchungsstapel) und 20 (Kontenbeschriftungen) | Quellen: README „Quellen und Referenzen" |

Support-Politik: Es wird jeweils die **letzte veröffentlichte Version**
unterstützt (Fehlerbehebungen erscheinen als Patch-Release, kein Backport).
Fehler bitte als Issue mit den Vorlagen unter `.github/ISSUE_TEMPLATE/`
melden – niemals mit echten Mandantendaten, sondern mit den Demodaten
(`testdaten/`) oder anonymisierten Ausschnitten. Sicherheitsrelevantes:
`SECURITY.md`.

## 5. Bewusst nicht zugesagt / offene Ausbaustufen

- Kein Backport auf ältere Releases; keine Zusage für Python < 3.10 oder
  Nicht-CPython-Interpreter.
- Externe Links (DATEV-Wissensplattform, gesetze-im-internet.de) werden
  nicht automatisch geprüft (Netzabhängigkeit, Portal-Anmeldung); geprüft
  werden alle **relativen** Repository-Links.
- Vollständige Kanonisierung der Soll-Katalogpunkte (eigene stabile ID je
  Katalogpunkt, README-Checkliste und Abdeckungsmatrix daraus generiert)
  ist Ausbaustufe; bis dahin gilt das ID-Konsistenz-Gate je Kapitel
  (`katalog_doku.pruefe_katalog_ids`).
- Fachliche Richtigkeit der Prüfregeln wird über die gesäten Fälle der
  Demodaten verifiziert; ein Ersatz für die berufsträgerseitige Würdigung
  ist der Bericht nicht (README „Datenschutz und Verantwortung").
