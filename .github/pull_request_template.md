## Was ändert dieser PR?

<!-- Kurz: Anlass (Issue/Befund), fachliche Änderung, betroffene Checks -->

## Checkliste

- [ ] `py werkzeuge/release_check.py` lokal grün (ggf. `--ohne-plugin-cli`)
- [ ] Prüflogik nur in `werkzeuge/` (kein Prompt), Schwellen über `konten_config.json`
- [ ] `befunde.KATALOG` und Soll-Katalog `werkzeuge/soll_katalog.json` konsistent; README-Prüfkatalog/Abdeckungsmatrix generiert, nicht von Hand editiert (`py werkzeuge/katalog_doku.py --write`, Gate `--check`)
- [ ] Erwartungsbilder `testdaten/erwartung.json` + `erwartung.md` nachgezogen (jeder gesäte Fall genau einmal)
- [ ] Externe Fakten mit Quellen-Link aus zulässigen Quellen (README/pruefkatalog.md)
- [ ] CHANGELOG-Eintrag (bei nutzersichtbarer Änderung)
- [ ] Keine echten Mandantendaten, keine Secrets, keine von Hand editierten generierten Dateien
