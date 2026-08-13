# JA-Agent – Jahresabschluss-Prüfplugin (DATEV)

Deterministische Prüf-Pipeline (Python) + KI-Beurteilungsschicht + Excel-Bericht.
Architektur, Katalog und Bedienung: README.md und skills/ja-pruefung/.

## Regeln für Arbeiten in diesem Projekt

- **Deterministik-Prinzip:** Eindeutige Prüfregeln gehören in
  `werkzeuge/checks.py` / `statistik.py` (+ Eintrag in `befunde.KATALOG` und
  `skills/ja-pruefung/references/pruefkatalog.md`) – niemals als
  Prompt-Anweisung. Die KI-Schicht beurteilt nur `llm_kandidaten.json`.
- Schwellwerte/Kontenbereiche nie hartkodieren – immer über
  `werkzeuge/konten_config.json`.
- Verifikation nach Änderungen: `py testdaten/erzeuge_testdaten.py`, dann
  `py werkzeuge/ja_pruefung.py --stapel testdaten --susa testdaten/SuSa_2025_Demo.csv --susa-vorjahr testdaten/SuSa_2024_Demo.csv --opos testdaten/OPOS_2025_Demo.csv --ausgabe testdaten/ausgabe`
  und stdout mit dem Erwartungsbild abgleichen (jeder gesäte Fehler genau
  einmal; keine neuen Scheinbefunde).
- `testdaten/ausgabe/` und CSV-Testdaten sind generiert – nicht von Hand
  editieren. Neue Version des Plugins: Version in `.claude-plugin/plugin.json`
  hochzählen und `dist/`-Paket neu bauen.
- Keine großen Datei-Dumps in den Chat; stdout-Zusammenfassungen genügen.
- **Quellenpflicht:** Externe Fakten (DATEV-Formate/Kategorien,
  Exportwege, gesetzliche Grenzen und Rechtsstände, Methodik-Schwellen)
  werden mit Quellen-Links direkt dort dokumentiert, wo sie gelesen
  werden – README „Quellen und Referenzen" bzw. die betroffene MD-Datei
  (z. B. pruefkatalog.md „Formatreferenzen"). Neue Behauptung ohne
  Quelle = nicht mergen.
