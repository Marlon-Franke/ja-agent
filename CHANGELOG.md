# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [SemVer](https://semver.org/lang/de/). Die Versionsnummer
steht synchron in `.claude-plugin/plugin.json` und `VERSION` in
`werkzeuge/ja_pruefung.py`; `py werkzeuge/baue_dist.py` erzwingt den
Gleichlauf. Git-Tags/GitHub-Releases gibt es ab 0.4.2; ältere Stände sind
aus `testdaten/erwartung.md` rekonstruiert (Datum = Repository-Upload).

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
