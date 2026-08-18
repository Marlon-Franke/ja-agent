# Sicherheitshinweise und Meldeweg

## Unterstützte Versionen

Sicherheitskorrekturen erscheinen ausschließlich für die **jeweils letzte
veröffentlichte Version** (siehe [Releases](https://github.com/Marlon-Franke/ja-agent/releases),
Support-Politik in `docs/test-strategy.md`).

## Vertrauliche Meldung

Bitte **keine** öffentlichen Issues für Sicherheitslücken. Meldeweg:

1. **GitHub Private Vulnerability Reporting** (bevorzugt): auf der
   Repository-Seite unter „Security → Report a vulnerability" – der Bericht
   ist nur für die Maintainer sichtbar
   ([GitHub-Doku](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)).
   Falls die Funktion im Repository noch nicht aktiviert ist:
2. **Direktnachricht an den Maintainer** über das GitHub-Profil
   [Marlon-Franke](https://github.com/Marlon-Franke) mit dem Betreff
   „ja-agent security".

Bitte angeben: betroffene Version/Commit, Reproduktionsschritte mit den
**Demodaten** (`testdaten/`) oder synthetischen Daten – niemals echte
Mandantendaten –, mögliche Auswirkung. Rückmeldung in der Regel innerhalb
von 7 Tagen; Behebung als Patch-Release mit Hinweis im CHANGELOG (ohne
Nennung des Meldenden, sofern nicht ausdrücklich gewünscht).

## Was das Werkzeug tut und was nicht

- Die Pipeline (`werkzeuge/`) läuft **vollständig lokal**, liest nur die
  übergebenen CSV-Dateien und schreibt in den Ausgabeordner; keine
  Netzwerkzugriffe, keine Telemetrie.
- An das Sprachmodell gehen ausschließlich die Kandidatenzeilen aus
  `llm_kandidaten.json` (README „Datenschutz und Verantwortung").
- Es werden keine Pakete automatisch installiert; fehlende Abhängigkeiten
  werden nur gemeldet (`werkzeuge/abhaengigkeiten.py`).
- Prüfsummen der Release-Artefakte stehen in `SHA256SUMS.txt` jedes
  Releases; die Archive sind reproduzierbar aus dem Tag baubar
  (`py werkzeuge/baue_dist.py`).

## Automatische Prüfungen

CI-Job `security`: Secret-Scan (gitleaks) über das Repository,
`pip-audit` gegen bekannte Schwachstellen der Laufzeitabhängigkeiten
(auch Teil von `release_check.py --streng`), Lizenzprüfung
(`pip-licenses`). Details: `docs/test-strategy.md`.
