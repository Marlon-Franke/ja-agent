# Erwartungsbild der Demo-Verifikation

Soll-Referenz für die beiden Verifikationsläufe aus CLAUDE.md auf den
generierten Demodaten (`py testdaten/erzeuge_testdaten.py`, 214
Buchungszeilen). Jeder Befund entspricht einem im Generator
kommentierten, gezielt gesäten Fall (`erzeuge_testdaten.py`); es dürfen
keine zusätzlichen Scheinbefunde auftreten. Bei Änderungen an Katalog,
Schwellwerten oder Generator ist diese Datei im selben Arbeitsgang
nachzuführen.

Kopfzeile beider Läufe: `JA-Prüfung v<Version> (72 Checks) | Demo GmbH |
01.01.2025 – 31.12.2025 | SKR03 automatisch erkannt (Indizien SKR03:
134, SKR04: 0) | 214 Buchungen aus 1 Stapel(n)`

## Lauf 1 – Standard (`--rechtsform kapitalgesellschaft`)

**Summen: 4 hoch / 30 mittel / 46 Hinweise | KI-Kandidaten: 22**

- hoch: AF-03 (1); RE-02 (1); SB-01 (1); ST-01 (1)
- mittel: AF-04 (1); AF-05 (1); DV-02 (1); ET-01 (1); KR-01 (1);
  OP-01 (1); OP-02 (1); OP-03 (2); OP-05 (3); PP-03 (1); PP-04 (1);
  RE-01 (1); SB-02 (1); SB-03 (1); SB-04 (1); SB-06 (1); ST-01 (2);
  ST-02 (3); US-01 (1); US-03 (1); US-04 (1); US-08 (1); VJ-01 (2)
- hinweis: AF-04 (1); BL-01 (2); BL-02 (1); BL-04 (1); CO-01 (1);
  DQ-01 (1); DV-01 (1); DV-03 (1); ET-02 (1); FR-02 (1); GS-01 (2);
  GV-01 (1); GV-02 (1); GV-03 (2); OP-04 (1); OP-05 (1); OP-06 (2);
  OP-07 (1); RE-03 (1); SB-05 (1); SB-08 (1); SB-09 (2); SD-01 (1);
  ST-03 (2); ST-04 (1); ST-05 (1); ST-07 (1); US-02 (1); US-03 (1);
  US-05 (4); US-07 (1); US-09 (1); US-10 (1); VJ-01 (1); VJ-02 (3)
- zusätzliche Prüfungen (Daten/Voraussetzung): PP-01, PP-02, SB-10
  (Rechtsform Kapitalgesellschaft – Privatkonten-Logik über PP-04);
  BL-05 (Konfiguration `latente_steuern` leer); FR-03 (Konfiguration
  `freigabegrenzen` leer); ST-08 (161 GuV-Buchungen < `benford_min_n`)

## Lauf 2 – Negativtest DQ-02 (`--rechtsform personengesellschaft`)

**Summen: 6 hoch / 29 mittel / 48 Hinweise | KI-Kandidaten: 22**

Abweichungen gegenüber Lauf 1 (alles Übrige identisch):

- hoch zusätzlich: **DQ-02 (2)** – Namens-Kürzel „GmbH" und
  KSt-Indizien widersprechen der Angabe Personengesellschaft
- mittel: PP-04 entfällt (Privatkonten bei PersG zulässig)
- hinweis zusätzlich: PP-01 (1), PP-02 (1) – Entnahme-Checks aktiv
- Skips: PP-04 (statt PP-01/02/SB-10); BL-05, FR-03, ST-08 unverändert

## Standardkonfigurations-Invarianten der v0.2.0-Präzisierungen

- ET-01 prüft netto (`vst_abzugsberechtigt: true`); der gesäte Fall
  (Geschenk 75,00 EUR netto) bleibt genau ein Mittel-Befund.
- US-04: Demodaten enthalten keinen nicht abziehbaren Anteil → weiterhin
  genau ein Mittel-Befund (Existenzfall); die Quotenprüfung
  (`bewirtung_nabz_quote_min`) feuert bei den Demodaten nicht.
- ST-04: `feiertage_zusatz` leer → unverändert ein Hinweis (So 13.07. +
  Feiertag 01.05.).
