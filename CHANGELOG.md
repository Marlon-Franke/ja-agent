# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [SemVer](https://semver.org/lang/de/). Die Versionsnummer
steht synchron in `.claude-plugin/plugin.json` und `VERSION` in
`werkzeuge/ja_pruefung.py`; `py werkzeuge/baue_dist.py` erzwingt den
Gleichlauf. Git-Tags/GitHub-Releases gibt es ab 0.4.2; ältere Stände sind
aus `testdaten/erwartung.md` rekonstruiert (Datum = Repository-Upload).

## [0.4.4] – 2026-08-18

Packaging-/Test-Gate-Release nach der Revisionsprüfung v0.4.3
(Befunde P0.1–P2.6); keine Änderung an Prüflogik oder Erwartungsbildern
(alle drei Referenzläufe unverändert).

### Behoben
- **P0.1** `requirements.txt` liegt jetzt im `.plugin`-Paket
  (Pflichteintrag der Archivprüfung); `werkzeuge/abhaengigkeiten.py`
  prüft `openpyxl` vor dem Import und meldet fehlende Pakete mit dem
  konkreten `pip install -r …/requirements.txt`-Befehl (Exit 2, keine
  automatische Installation) – `ja_pruefung.py --help` und
  `llm_einarbeiten.py` funktionieren ohne installierte Drittpakete;
  SKILL.md verlangt den Preflight vor dem ersten Pipelineaufruf.
- `claude plugin validate .claude-plugin/plugin.json --strict` meldete
  „CLAUDE.md at the plugin root is not loaded as project context" (die
  Prüfung von `.` validiert nur das Marketplace-Manifest) → Projektanweisungen
  nach `.claude/CLAUDE.md` verschoben (gleichwertiger Ort laut
  Claude-Code-Doku „Memory"); Build-Gate gegen Rückfall.
- Katalogdrift README ↔ Abdeckungsmatrix (Kap. 2: `ST-04` als Teilabdeckung
  „ungewöhnliche Zeiten/Benutzer"; Kap. 8: Skip-Hinweis `PP-01/02`, `SB-10`
  bei KapG) angeglichen – gefunden vom neuen ID-Konsistenz-Gate.
- `requirements.txt`: Kommentar verwies auf ein nicht vorhandenes
  `docs/test-strategy` → Datei existiert jetzt; getestete Spanne
  `openpyxl>=3.1,<4`.
- Ungenutzte Importe (`dataclasses.field`, `befunde.eur`) entfernt (ruff).

### Hinzugefügt
- **P1.1** `werkzeuge/release_check.py`: kanonischer Release-Check (ein
  Befehl, ein Exit-Code) – Umgebung, Syntax, Sollstruktur, Testdaten,
  drei Referenzläufe, Markdown-Links, `claude plugin validate --strict`
  (beide Manifeste), reproduzierbarer Build, ruff/pip-audit; README,
  `.claude/CLAUDE.md` und CI rufen denselben Befehl.
- **P1.2** `testdaten/erwartung.json` + `werkzeuge/pruefe_erwartung.py`:
  maschinenlesbares Erwartungsbild aller 73 Checks je Lauf (Status
  aktiv/skip, Treffer je Schwere, Belege gesäter Fälle, Skip-Gründe,
  Summen, KI-Kandidaten, stdout-Kopf) statt Summen-Grep; die bisher nicht
  ausgewiesenen Nullbefunde AF-01, AF-02, BL-03, FR-01, FR-04, SB-07,
  ST-06, US-06 sind damit explizit.
- **P0.2** CI: Job `release-check` mit gepinnter Claude-Code-CLI (2.1.201)
  und offizieller Strict-Validierung; Job `marketplace` (lokaler
  Marketplace-Lebenszyklus add/install/list/details/update/uninstall mit
  isoliertem `CLAUDE_CONFIG_DIR`); Job `paket` (entpacktes `.plugin` in
  frischer venv, Negativtest ohne `openpyxl`, Lauf über den Paketpfad).
- **P1.4** CI-Matrix Ubuntu/Windows/macOS × Python 3.10–3.14; Job
  `reproduzierbarkeit` vergleicht die Archiv-Prüfsummen aller Zellen;
  `docs/test-strategy.md` mit Kompatibilitäts- und Supportzusagen
  (inkl. minimaler Claude-Code-Version).
- **P1.5** `katalog_doku.pruefe_katalog_ids`: README-Checkliste,
  Abdeckungsmatrix und `befunde.KATALOG` müssen je Kapitel dieselben
  CHECK-IDs führen (Build-Gate).
- **P2.1** Referenzkatalog trägt einen generierten Referenzstand-Block
  (Version = `plugin.json`, Build-Gate) sowie fachlichen Rechtsstand und
  Datum der letzten fachlichen Durchsicht.
- **P2.2** `ruff.toml` (Fehlerklassen-Regelsatz), `requirements-dev.txt`
  (ruff, pip-audit, pip-licenses), CI-Job `security` (gitleaks,
  pip-audit, Lizenzprüfung).
- **P2.3** `baue_dist.py` baut aus dem Git-Objektspeicher des Commits
  (`git ls-tree`/`cat-file`, Commit-Zeitstempel, `ZIP_STORED`, feste
  Rechte) → byteidentisch reproduzierbar auf allen Plattformen; sauberer
  Arbeitsbaum erzwungen (`--erlaube-schmutzig`), `dist/SHA256SUMS.txt`
  wird mitgeschrieben; `.gitattributes` fixiert Zeilenenden;
  `.github/workflows/release.yml` baut bei Tag `v*` aus dem Tag und
  veröffentlicht das GitHub-Release mit Artefakten und Prüfsummen
  (`werkzeuge/release_notes.py` liefert die Notizen aus dem CHANGELOG).
- **P2.4** README: Release-Download für Claude Desktop/Cowork an erster
  Stelle, Marketplace für Claude Code, lokaler Build als
  Contributor-Variante; Voraussetzungen (Python 3.10–3.14, `py`/`python3`,
  Abhängigkeit, Claude-Code-Referenzversion); CI-/Release-Badges.
- **P2.5** `CONTRIBUTING.md`, `SECURITY.md` (vertraulicher Meldeweg),
  Issue-Vorlagen, PR-Vorlage, `CODEOWNERS`.

### Offen (Repository-Einstellungen, nicht per Commit lösbar)
- **P1.3** Branch-Schutz/Ruleset für `main` mit erforderlichen CI-Checks;
  **P2.6** GitHub-Repositorybeschreibung und Topics – vom
  Repository-Eigentümer zu setzen (docs/test-strategy.md, Abschnitt 2).

## [0.4.3] – 2026-08-18

Klärung der Klassifikationsdrift (Release-Readiness-Report Befunde 5–9);
keine Änderung an Prüflogik oder Erwartungsbildern.

### Geändert
- Semantik festgelegt: Die `[R]/[P]/[A]/[X]`-Tags an den Katalogpunkten in
  README und Abdeckungsmatrix sind die Klasse des Soll-Katalogpunkts (1:1 aus
  dem Referenzkatalog); Ebene und Klasse des implementierten Checks führt
  allein `befunde.KATALOG` – beides darf abweichen. README (Legende) und
  Matrix benennen das jetzt ausdrücklich.
- Abdeckungsmatrix: Ebenen-Tabelle wird aus `befunde.KATALOG` generiert;
  dabei korrigiert: RE-03 (Ebene 3 statt 2), ST-03 (Ebene 4 statt 3).

### Behoben
- `.gitignore`: `JA-Pruefung/` (Standard-Ausgabeordner) griff auf
  case-insensitiven Dateisystemen (Windows/macOS) auch auf den Skill-Ordner
  `skills/ja-pruefung/` – neue Skill-Dateien wären dort still ignoriert
  worden; ausdrücklich re-inkludiert.

### Hinzugefügt
- `werkzeuge/katalog_doku.py` (`--write`/`--check`): generiert Ebenen-Tabelle
  und ein neues Check-Register (ID, Name, Bereich, Ebene, Klasse) in
  `skills/ja-pruefung/references/pruefkatalog.md`; `baue_dist.py` prüft die
  Aktualität als Build-Gate (damit auch CI).

## [0.4.2] – 2026-08-18

Release-Readiness-Runde (Report vom 18.08.2026, PRs #1, #2 und dieses
Release): keine fachlichen Änderungen am Prüfkatalog (73 Checks, Erwartungs-
bilder unverändert), ausschließlich Paketierung, Validierung, CI und
Dokumentation.

### Behoben
- Plugin-/Marketplace-Manifeste hießen im Repository endungslos
  (`.claude-plugin/plugin`, `.claude-plugin/marketplace`) und waren damit
  nicht installierbar → `plugin.json` / `marketplace.json`.
- Toter Link auf den Soll-Prüfkatalog im Plugin-Paket (Referenzdatei liegt
  nur im Repository) → absoluter GitHub-Link.
- README: Skill-Aufruf `/jahresabschluss-agent:ja-pruefung` (Plugin-
  Namensraum) statt `/ja-pruefung`; Buildschritt in der Installations-
  anleitung; Marketplace direkt aus GitHub (`Marlon-Franke/ja-agent`).

### Hinzugefügt
- Release-Validierung in `werkzeuge/baue_dist.py`: Manifeste vorhanden und
  gültig, Pluginname in beiden Manifesten, Versionsgleichlauf, SKILL-
  Frontmatter, Checkzahl (`<n> Checks` in README/SKILL.md/plugin.json =
  `len(befunde.KATALOG)`), Archivinhalt inkl. PBIP-Vorlage; jeder Verstoß
  bricht den Build ab.
- GitHub-ZIP wird aus dem Git-Index (`git ls-files`) gebaut – ungetrackte
  Dateien gelangen nicht mehr ins Paket.
- CI (`.github/workflows/ci.yml`): Syntaxprüfung, Manifest-Check, Testdaten,
  Standardlauf gegen Erwartungsbild (4 hoch / 30 mittel / 47 Hinweise, keine
  Bilanzprobe-Warnung), Negativtest DQ-02, Zusatztest CO-02, Distributions-
  bau mit Release-Validierung.
- `requirements.txt` (`openpyxl>=3.1`).
- Manifest-Metadaten: `author`, `homepage`, `repository`, Marketplace-
  `description` und Owner `Marlon-Franke`.
- `werkzeuge/pbi_vorlage/*/.platform` versioniert (Teil der PBIP-Vorlage,
  die `--pbi` in jede Ausgabe kopiert).
- Dieses Changelog.

### Bekannt / offen
- Klassifikationsdrift zwischen README-Checkliste, Abdeckungsmatrix und
  `befunde.KATALOG` (Ebene bei RE-03/ST-03; Klasse R/P/A bei 28 Checks):
  Analyse liegt vor, fachliche Entscheidung und Generierung der Doku aus
  `befunde.KATALOG` folgen in einem eigenen Release.

## [0.4.1] – 2026-08-13

- Volumen-Skalierung der Testdaten auf 1.504 Buchungszeilen mit
  unveränderten gesäten Fehlerbildern; Erwartungsbilder entsprechend
  (`testdaten/erwartung.md`, „Volumen-Invarianten der v0.4.1-Skalierung").
- Power-BI-Bericht (`--pbi`, PBIP-Vorlage mit fünf verknüpften Tabellen und
  sieben Berichtsseiten).

## [0.4.0] – 2026-08

- Cut-off-Prüfungen CO-01 (Erlöse vor WJ-Ende) und CO-02 (Aufwand nach
  WJ-Ende, fakultativ mit `--stapel-folgejahr`) sowie Bilanz-Überarbeitung
  (`testdaten/erwartung.md`, „Cut-off- und Bilanz-Invarianten").

## [0.3.1] – 2026

- Vorjahres-Korrektur (VJ-Checks, doppisch schließende Vorjahres-SuSa;
  `testdaten/erwartung.md`, „Vorjahres-Invarianten").

## [0.2.0] – 2026

- Präzisierungen der Standardkonfiguration (`werkzeuge/konten_config.json`;
  `testdaten/erwartung.md`, „Standardkonfigurations-Invarianten").
