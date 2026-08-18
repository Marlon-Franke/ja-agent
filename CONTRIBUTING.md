# Beiträge zum JA-Agent

Danke für das Interesse. Der JA-Agent ist ein Prüfwerkzeug für
Berufsträger; Änderungen an Prüflogik müssen nachvollziehbar, belegt und
deterministisch verifizierbar sein. Die folgenden Regeln sind kurz, aber
verbindlich (Details: `.claude/CLAUDE.md`, `docs/test-strategy.md`).

## Ablauf

1. **Issue zuerst** für fachliche Änderungen (neuer Check, geänderte
   Schwelle, Katalogänderung) – Vorlagen unter `.github/ISSUE_TEMPLATE/`.
   Reine Tippfehler/Doku-Korrekturen brauchen kein Issue.
2. **Branch** vom aktuellen `main`, sprechender Name
   (`fix/...`, `feat/...`, `docs/...`, `release/...`).
3. **Entwickeln** nach den Projektregeln:
   - Eindeutige Regeln gehören in `werkzeuge/checks*.py`/`statistik.py`
     + `befunde.KATALOG` + Katalogdokumentation, nie ins Prompt.
   - Schwellwerte/Kontenbereiche nur über `werkzeuge/konten_config.json`.
   - Externe Fakten nur mit Quellen-Link aus zulässigen Quellen (amtliche
     Primärquellen, DATEV-eigene Dokumente, code.claude.com/docs,
     docs.github.com) direkt an der Lesestelle.
   - Neue Python-Abhängigkeit: `requirements.txt` **und**
     `werkzeuge/abhaengigkeiten.PAKETE`; Import erst nach dem Preflight.
   - Erwartungsbilder (`testdaten/erwartung.json` und `erwartung.md`) im
     selben Arbeitsgang nachziehen; jeder gesäte Fall genau einmal.
4. **Verifizieren** – ein Befehl, muss grün sein:

   ```bash
   py werkzeuge/release_check.py
   ```

   (ohne installierte Claude-CLI: `--ohne-plugin-cli`; vor dem Commit:
   `--erlaube-schmutzig`; mit ruff/pip-audit: `pip install -r
   requirements-dev.txt` und `--streng`).
5. **Pull Request** gegen `main` mit der PR-Vorlage; die CI muss grün sein
   (Release-Check, Marketplace-Lebenszyklus, Paketlauf, Matrix,
   Reproduzierbarkeit, Security). Kein Merge mit rotem Check.
6. **Release** (nur Maintainer): Version in `.claude-plugin/plugin.json`
   und `VERSION` in `werkzeuge/ja_pruefung.py` hochzählen,
   `py werkzeuge/katalog_doku.py --write`, CHANGELOG-Abschnitt, Merge,
   annotierter Tag `vX.Y.Z` → `release.yml` veröffentlicht die Artefakte.

## Was nicht in Beiträge gehört

- Echte Mandantendaten (auch nicht anonymisiert „ein bisschen"): Testfälle
  ausschließlich über `testdaten/erzeuge_testdaten.py` (synthetisch,
  kommentiert gesät).
- Zugangsdaten, Tokens, Lizenzschlüssel (Secret-Scan in der CI).
- Drittquellen (Verlage, Kanzleien, Blogs) als Beleg in Repo-Dateien.
- Generierte Dateien von Hand editiert (`testdaten/*.csv`,
  `testdaten/ausgabe/`, generierte Doku-Blöcke, `dist/`).

## Stil

Python ≥ 3.10, Typannotationen wie im Bestand, deutsche Bezeichner und
Kommentare (Fachdomäne), `ruff.toml` als Mindeststandard. Commit-Nachrichten
auf Deutsch, Betreff ≤ 72 Zeichen, Bezug auf Issue/Befund im Text.

## Lizenz

Mit einem Beitrag erklärst du dich einverstanden, dass er unter der
MIT-Lizenz des Projekts (`LICENSE`) veröffentlicht wird.
