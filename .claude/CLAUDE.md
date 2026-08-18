# JA-Agent – Jahresabschluss-Prüfplugin (DATEV)

Deterministische Prüf-Pipeline (Python) + KI-Beurteilungsschicht + Excel-Bericht.
Architektur, Katalog und Bedienung: README.md und skills/ja-pruefung/.
Diese Datei liegt bewusst in `.claude/CLAUDE.md` (Projektanweisungen laut
[Claude-Code-Doku „Memory"](https://code.claude.com/docs/en/memory)):
eine `CLAUDE.md` an der Plugin-Wurzel meldet `claude plugin validate --strict`
als Warnung („wird nicht als Plugin-Kontext geladen") – Build-Gate in
`baue_dist.py`.

## Regeln für Arbeiten in diesem Projekt

- **Deterministik-Prinzip:** Eindeutige Prüfregeln gehören in
  `werkzeuge/checks.py` / `statistik.py` (+ Eintrag in `befunde.KATALOG` und
  `skills/ja-pruefung/references/pruefkatalog.md`) – niemals als
  Prompt-Anweisung. Die KI-Schicht beurteilt nur `llm_kandidaten.json`.
  Checkzahl-Angaben in README (2×), SKILL.md und plugin.json folgen
  `len(befunde.KATALOG)`; Excel-Deckblatt und stdout-Kopf zählen
  automatisch.
- Ebenen-Tabelle und Check-Register in `pruefkatalog.md` sowie der
  Referenzstand-Block im Referenzkatalog sind generiert
  (`py werkzeuge/katalog_doku.py --write`, Gate im Build) – nicht von Hand
  editieren; Klassifikation ändern heißt `befunde.KATALOG` ändern.
  `[R]/[P]/[A]`-Tags an Katalogpunkten = Soll-Klasse des Referenzkatalogs.
  README-Checkliste (`### 1.`–`### 20.`) und Abdeckungsmatrix (`## 1.`–
  `## 20.`) müssen je Kapitel dieselben CHECK-IDs nennen (Gate) – eine
  Zuordnung immer in beiden Dokumenten ändern.
- Schwellwerte/Kontenbereiche nie hartkodieren – immer über
  `werkzeuge/konten_config.json`.
- **Laufzeitabhängigkeiten:** nur `requirements.txt` (`openpyxl`); neue
  Pakete dort UND in `werkzeuge/abhaengigkeiten.PAKETE` eintragen. Module,
  die Drittpakete importieren, erst nach `abhaengigkeiten.pruefe_oder_beende()`
  laden (klare Meldung statt Traceback; `--help` bleibt abhängigkeitsfrei).
- **Verifikation nach Änderungen – ein Befehl (kanonischer Release-Check,
  identisch in README und CI):**
  `py werkzeuge/release_check.py` (lokal ohne Claude-CLI:
  `--ohne-plugin-cli`; vor dem Commit: `--erlaube-schmutzig`). Er führt
  Syntaxprüfung, Sollstruktur, Testdaten-Generator, die drei Referenzläufe
  gegen `testdaten/erwartung.json` (alle 73 Checks je Lauf: Standard,
  Negativtest DQ-02 mit `--rechtsform personengesellschaft` = zwei
  Hoch-Befunde, Zusatztest CO-02 mit `--stapel-folgejahr` = genau ein
  Hinweis; nie eine `WARNUNG: Bilanzprobe`-Zeile), Markdown-Links,
  `claude plugin validate --strict`, den reproduzierbaren Distributionsbau
  und – wenn installiert – ruff/pip-audit aus. Erwartungsbilder ändern
  heißt `testdaten/erwartung.json` UND `testdaten/erwartung.md` im selben
  Arbeitsgang nachziehen (jeder gesäte Fehler genau einmal, keine
  Scheinbefunde). Demo-Mandant ist eine GmbH (Projektvorgabe):
  Privatkonten-Buchungen sind dort PP-04-Befunde, PP-01/02 und SB-10
  zeigen den Rechtsform-Skip; PersG-Spezifika (Kapitalkonten, Sonder-/
  Ergänzungsbilanzen, § 15a EStG) sind Katalog-Ausbaustufen.
- `testdaten/ausgabe/` und CSV-Testdaten sind generiert – nicht von Hand
  editieren (Gate: Generator-Ausgabe == versionierte CSVs). Neue Version
  des Plugins: Version in `.claude-plugin/plugin.json` hochzählen (synchron
  `VERSION` in `werkzeuge/ja_pruefung.py`), `py werkzeuge/katalog_doku.py
  --write` (Referenzstand), CHANGELOG-Abschnitt `## [x.y.z] – JJJJ-MM-TT`
  anlegen, Release-Check grün, mergen, annotierten Tag `vx.y.z` pushen –
  der Workflow `release.yml` baut die Artefakte aus dem Tag und
  veröffentlicht das GitHub-Release mit `SHA256SUMS.txt`
  (`py werkzeuge/baue_dist.py` baut lokal reproduzierbar dieselben Archive
  aus dem Commit; `dist/` ist gitignored).
- Keine großen Datei-Dumps in den Chat; stdout-Zusammenfassungen genügen.
- **Quellenpflicht:** Externe Fakten (DATEV-Formate/Kategorien,
  Exportwege, gesetzliche Grenzen und Rechtsstände, Methodik-Schwellen,
  Claude-Code-Plugin-Mechanik) werden mit Quellen-Links direkt dort
  dokumentiert, wo sie gelesen werden – README „Quellen und Referenzen"
  bzw. die betroffene MD-Datei (z. B. pruefkatalog.md „Formatreferenzen").
  Neue Behauptung ohne Quelle = nicht mergen.
- **Zulässige Quellen (abschließend):** Rechtsfragen NUR amtliche
  Primärquellen (gesetze-im-internet.de, BGBl über recht.bund.de,
  BStBl-/BMF-Schreiben); DATEV-/Formatfragen NUR DATEV-eigene Dokumente
  (Wissensplattform/Hilfe-Center, Developer-Portal); Claude-Code-Fragen NUR
  code.claude.com/docs; GitHub-/CI-Fragen NUR docs.github.com. Drittquellen
  (Verlage, Kanzleien, Banken, Blogs) sind in Repo-Dateien verboten –
  auch nicht ergänzend.
- Beiträge, Support-/Kompatibilitätszusagen und Sicherheitsmeldungen:
  CONTRIBUTING.md, docs/test-strategy.md, SECURITY.md.
