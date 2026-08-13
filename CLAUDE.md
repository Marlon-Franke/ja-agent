# JA-Agent – Jahresabschluss-Prüfplugin (DATEV)

Deterministische Prüf-Pipeline (Python) + KI-Beurteilungsschicht + Excel-Bericht + Power BI Report.
Architektur, Katalog und Bedienung: README.md und skills/ja-pruefung/.

## Regeln für Arbeiten in diesem Projekt

- **Deterministik-Prinzip:** Eindeutige Prüfregeln gehören in
  `werkzeuge/checks.py` / `statistik.py` (+ Eintrag in `befunde.KATALOG` und
  `skills/ja-pruefung/references/pruefkatalog.md`) – niemals als
  Prompt-Anweisung. Die KI-Schicht beurteilt nur `llm_kandidaten.json`.
  Checkzahl-Angaben in README (2×), SKILL.md und plugin.json folgen
  `len(befunde.KATALOG)`; Excel-Deckblatt und stdout-Kopf zählen
  automatisch.
- Schwellwerte/Kontenbereiche nie hartkodieren – immer über
  `werkzeuge/konten_config.json`.
- Verifikation nach Änderungen: `py testdaten/erzeuge_testdaten.py`, dann
  `py werkzeuge/ja_pruefung.py --stapel testdaten --susa testdaten/SuSa_2025_Demo.csv --susa-vorjahr testdaten/SuSa_2024_Demo.csv --opos testdaten/OPOS_2025_Demo.csv --mandant "Demo GmbH" --rechtsform kapitalgesellschaft --ausgabe testdaten/ausgabe`
  und stdout mit dem Erwartungsbild in `testdaten/erwartung.md` abgleichen
  (jeder gesäte Fehler genau einmal; keine neuen Scheinbefunde). Negativtest DQ-02: derselbe Aufruf
  mit `--rechtsform personengesellschaft` muss zwei Hoch-Befunde liefern
  (Namens-Kürzel „GmbH" und KSt-Indizien widersprechen). Demo-Mandant ist
  eine GmbH
  (Projektvorgabe): Privatkonten-Buchungen sind dort PP-04-Befunde,
  PP-01/02 und SB-10 zeigen den Rechtsform-Skip; PersG-Spezifika
  (Kapitalkonten, Sonder-/Ergänzungsbilanzen, § 15a EStG) sind
  Katalog-Ausbaustufen.
- `testdaten/ausgabe/` und CSV-Testdaten sind generiert – nicht von Hand
  editieren. Neue Version des Plugins: Version in `.claude-plugin/plugin.json`
  hochzählen (synchron `VERSION` in `werkzeuge/ja_pruefung.py`) und beide
  Pakete mit `py werkzeuge/baue_dist.py` neu bauen (schreibt ZIP-konforme
  Pfade und lässt `__pycache__`, `testdaten/ausgabe/` und `dist/` aus).
- Keine großen Datei-Dumps in den Chat; stdout-Zusammenfassungen genügen.
- **Quellenpflicht:** Externe Fakten (DATEV-Formate/Kategorien,
  Exportwege, gesetzliche Grenzen und Rechtsstände, Methodik-Schwellen)
  werden mit Quellen-Links direkt dort dokumentiert, wo sie gelesen
  werden – README „Quellen und Referenzen" bzw. die betroffene MD-Datei
  (z. B. pruefkatalog.md „Formatreferenzen"). Neue Behauptung ohne
  Quelle = nicht mergen.
- **Zulässige Quellen (abschließend):** Rechtsfragen NUR amtliche
  Primärquellen (gesetze-im-internet.de, BGBl über recht.bund.de,
  BStBl-/BMF-Schreiben); DATEV-/Formatfragen NUR DATEV-eigene Dokumente
  (Wissensplattform/Hilfe-Center, Developer-Portal). Drittquellen
  (Verlage, Kanzleien, Banken, Blogs) sind in Repo-Dateien verboten –
  auch nicht ergänzend.
