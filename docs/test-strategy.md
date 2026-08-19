# Teststrategie, Kompatibilitäts- und Supportzusagen

Stand: Release 0.4.5 (2026-08-19; Governance-Härtung und Kanonisierung des Soll-Katalogs nach Revisionsprüfung v0.4.4). Diese Datei ist die verbindliche
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
| 3 | Plugin-Sollstruktur: Manifeste, Versionsgleichlauf, Checkzahl, SKILL-Frontmatter, generierte Doku-Blöcke (README-Prüfkatalog, Abdeckungsmatrix, Ebenen-Tabelle, Check-Register, Referenzstand), kanonischer Soll-Katalog (`werkzeuge/soll_katalog.json`: Soll-IDs, Status, CHECK-IDs ↔ `befunde.KATALOG` ohne verwaiste Checks, Referenzkatalog-Zeilen 1:1 zugeordnet, Soll-Klasse = Referenzklassen), keine fremden CHECK-IDs in README/Matrix, `CLAUDE.md`-Ablage | `werkzeuge/baue_dist.py`, `werkzeuge/katalog_doku.py`, `werkzeuge/soll_katalog.json` |
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

`main` ist durch das Repository-**Ruleset „main-schutz"** (ID 21009901,
aktiv seit 2026-08-18) abgesichert: Änderungen nur per Pull Request (Merge
oder Squash), kein Direkt-/Force-Push, kein Löschen, **Required Status
Checks** `release-check`, `marketplace`, `paket`, `reproduzierbarkeit`,
`security` (strict: Branch muss aktuell sein); kein Bypass, auch nicht für
den Eigentümer. Nachweis: `gh api repos/Marlon-Franke/ja-agent/rules/branches/main`
(die Legacy-Branch-API `…/branches/main` zeigt Rulesets **nicht** – dort
erscheint `required_status_checks: off`, obwohl die Checks erzwungen werden;
[About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)).
Die Kontexte entsprechen den Job-`name`-Werten in `ci.yml`; wer einen Job
umbenennt, muss das Ruleset nachziehen, sonst blockiert es jeden Merge.
Alle Actions sind auf Commit-SHAs gepinnt (Node-24-Majors; Node 20 wird am
16.09.2026 von den GitHub-Runnern entfernt); `.github/dependabot.yml`
liefert Aktualisierungen als PR durch die CI.

## 3. Release-Workflow (`.github/workflows/release.yml`)

Auslöser: Push eines annotierten Tags `v<major>.<minor>.<patch>`. Schritte:
Tag annotiert, **Tag-Commit liegt auf `main`** (`git merge-base
--is-ancestor`), **mindestens ein erfolgreicher CI-Lauf für genau diesen
Commit** (sonst erst CI abwarten und per `workflow_dispatch` erneut
auslösen), Tag == `version` in `plugin.json`, CHANGELOG-Abschnitt vorhanden
(sonst jeweils Abbruch), `release_check.py --streng` mit Claude-CLI, Distributionsbau **aus dem Tag** (Inhalte aus dem
Git-Objektspeicher, Commit-Zeitstempel, `ZIP_STORED` → byteidentisch
reproduzierbar), Release-Notes = CHANGELOG-Abschnitt der Version
(`werkzeuge/release_notes.py`), Veröffentlichung mit `gh release create`
inkl. `jahresabschluss-agent.plugin`, `jahresabschluss-agent_GitHub.zip`,
`SHA256SUMS.txt`. Jeder kann die Prüfsummen lokal nachvollziehen:
`git checkout v<version> && py werkzeuge/baue_dist.py` liefert dieselben
Werte.

## 4. Kompatibilitätsmatrix und Support

| Komponente | Unterstützt | Nachweis | Hinweis |
|---|---|---|---|
| Python | 3.10, 3.11, 3.12, 3.13, 3.14 (CPython) | **automatisch** (CI-Matrix) | ältere Versionen: `abhaengigkeiten`/`release_check` melden `< 3.10` als Fehler |
| Betriebssystem | Windows 10/11, Ubuntu (aktuelle LTS), macOS (aktuell) | **automatisch** (CI-Matrix, Runner-Images `-latest`) | Befehle im README mit `py` (Windows) bzw. `python3` |
| `openpyxl` | `>=3.1,<4` | **automatisch** (Matrix, Paketlauf) | Obergrenze bewusst: neue Major-Version erst nach Matrixlauf freigeben |
| Claude Code CLI | Referenzversion **2.1.201** (in CI gepinnt) | **automatisch** (Strict-Validierung, Marketplace-Lebenszyklus) | neuere Versionen werden mit dem Pin-Update in `ci.yml` freigegeben; ältere ungetestet |
| Claude Desktop / Cowork | Plugin-Import über die `.plugin`-Datei des Releases | **manuell** (Release-Checkliste, Abschnitt 6; nicht automatisierbar) | gleiches Archiv wie der CLI-Weg; Import, Aktivierung und Skill-Aufruf in der UI werden von der CI **nicht** geprüft |
| DATEV-Format | EXTF/DTVF Version 700, Kategorien 21 (Buchungsstapel) und 20 (Kontenbeschriftungen) | automatisch (Demodaten) / Quellen manuell | Quellen: README „Quellen und Referenzen" |

Support-Politik: Es wird jeweils die **letzte veröffentlichte Version**
unterstützt (Fehlerbehebungen erscheinen als Patch-Release, kein Backport).
Fehler bitte als Issue mit den Vorlagen unter `.github/ISSUE_TEMPLATE/`
melden – niemals mit echten Mandantendaten, sondern mit den Demodaten
(`testdaten/`) oder anonymisierten Ausschnitten. Sicherheitsrelevantes:
`SECURITY.md`.

## 5. Bewusst nicht zugesagt / offene Ausbaustufen

- Kein Backport auf ältere Releases; keine Zusage für Python < 3.10 oder
  Nicht-CPython-Interpreter.
- Externe Links sind kein PR-Gate, werden aber **monatlich** (Workflow
  `linkcheck.yml`, `werkzeuge/pruefe_links_extern.py`, tolerant mit
  Wiederholung) geprüft; als Linkalterung gilt nur HTTP 404/410, Timeouts
  und Zugriffsschutz werden als „nicht prüfbar" gemeldet
  (`www.gesetze-im-internet.de` antwortet GitHub-Runnern nicht, lokal ist
  es erreichbar – lokaler Lauf `py werkzeuge/pruefe_links_extern.py` als
  Teil der Release-Checkliste); DATEV-Domains sind dokumentierte Ausnahmen, weil
  die Portale als Single-Page-Anwendung auch für nicht existierende
  Dokument-IDs HTTP 200 liefern – ihre Existenz ist nur manuell prüfbar
  (Release-Checkliste). Geprüft als Gate werden alle **relativen**
  Repository-Links.
- Soll-Katalogpunkte sind seit 0.4.5 kanonisiert
  (`werkzeuge/soll_katalog.json`, Gate 3): Der Referenzkatalog selbst bleibt
  ein handgepflegtes Fachdokument; das Gate stellt nur sicher, dass jede
  seiner Checkbox-Zeilen genau einem Soll-Punkt zugeordnet ist und die
  Soll-Klassen übereinstimmen – die fachliche Richtigkeit der Zuordnung
  (welcher Check welchen Soll-Punkt wie weit abdeckt) ist Review-Gegenstand
  des jeweiligen PR, nicht automatisiert. Punkte mit Status „Ausbaustufe"
  (`offen`) und ➕-Zusätze sind bewusst offene Roadmap, keine Zusage.
- Fachliche Richtigkeit der Prüfregeln wird über die gesäten Fälle der
  Demodaten verifiziert; ein Ersatz für die berufsträgerseitige Würdigung
  ist der Bericht nicht (README „Datenschutz und Verantwortung").

## 6. Manuelle Release-Checkliste (Claude Desktop / Cowork, DATEV-Quellen)

Was die CI nicht abdecken kann, wird je Release von Hand geprüft und hier
protokolliert (Prüfer, Datum, Ergebnis). Ohne Eintrag gilt der Weg für
dieses Release als **nicht geprüft** – nicht als fehlerhaft.

Schritte:

1. `jahresabschluss-agent.plugin` des Releases laden, Prüfsumme gegen
   `SHA256SUMS.txt` vergleichen.
2. In Claude Desktop/Cowork importieren; Plugin erscheint in der
   Plugin-Verwaltung und ist aktiviert.
3. Skill `/jahresabschluss-agent:ja-pruefung` ist sichtbar; Aufruf mit den
   Demodaten (`testdaten/`, Aufruf aus README) liefert die Summenzeile
   `4 hoch / 30 mittel / 47 Hinweise | KI-Kandidaten: 22`; fehlt
   `openpyxl`, erscheint der Installationshinweis (Exit 2) statt eines
   Tracebacks.
4. Deinstallation über die Plugin-Verwaltung ohne Rückstände.
5. DATEV-Quellenlinks (README „Quellen und Referenzen", Abschnitt
   Formatreferenzen) stichprobenartig im Browser öffnen – Dokument-IDs
   existieren (Portale liefern auch für falsche IDs HTTP 200); zusätzlich
   lokal `py werkzeuge/pruefe_links_extern.py` (erreicht auch
   gesetze-im-internet.de, das GitHub-Runnern nicht antwortet).

| Release | Desktop/Cowork-Import (Schritte 1–4) | DATEV-Links (Schritt 5) | Prüfer / Datum |
|---|---|---|---|
| v0.4.4 | offen | offen | – |
| v0.4.5 | offen | offen | – |
