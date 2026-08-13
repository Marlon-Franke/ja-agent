# Erwartungsbild der Demo-Verifikation

Soll-Referenz für die drei Verifikationsläufe aus CLAUDE.md auf den
generierten Demodaten (`py testdaten/erzeuge_testdaten.py`, 1.504
Buchungszeilen + 6 Zeilen Folgejahres-Stapel in
`testdaten/folgejahr/`). Jeder Befund entspricht einem im Generator
kommentierten, gezielt gesäten Fall (`erzeuge_testdaten.py`); es dürfen
keine zusätzlichen Scheinbefunde auftreten. Die seit v0.4.1 enthaltenen
Volumen-Füllbuchungen (realistische Kleinst-KapG, siehe Abschnitt
„Volumen-Invarianten") sind konstruktiv befundneutral. Bei Änderungen
an Katalog, Schwellwerten oder Generator ist diese Datei im selben
Arbeitsgang nachzuführen.

Kopfzeile aller Läufe: `JA-Prüfung v<Version> (73 Checks) | Demo GmbH |
01.01.2025 – 31.12.2025 | SKR03 automatisch erkannt (Indizien SKR03:
474, SKR04: 0) | 1504 Buchungen aus 1 Stapel(n)`

Kein Lauf darf eine `WARNUNG: Bilanzprobe weicht von 0,00 ab`-Zeile
ausgeben (Kennzahl „Bilanzprobe Aktiva − Passiva" = 0,00 EUR in beiden
Jahren; Bilanzsumme 402.503,05 EUR, Vorjahr 333.437,43 EUR,
Jahresergebnis +213.433,75 EUR, Vorjahr +183.967,43 EUR).

## Lauf 1 – Standard (`--rechtsform kapitalgesellschaft`)

**Summen: 4 hoch / 30 mittel / 47 Hinweise | KI-Kandidaten: 22**

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
  US-05 (4); US-07 (1); US-09 (1); US-10 (1); VJ-01 (2); VJ-02 (3)
- zusätzliche Prüfungen (Daten/Voraussetzung): PP-01, PP-02, SB-10
  (Rechtsform Kapitalgesellschaft – Privatkonten-Logik über PP-04);
  BL-05 (Konfiguration `latente_steuern` leer); **CO-02 (fakultativ –
  Folgejahres-Stapel nicht geliefert; kein Mangel)**; FR-03
  (Konfiguration `freigabegrenzen` leer)
- ST-08 (Benford) läuft seit der Volumen-Skalierung aktiv
  (GuV-Buchungen > `benford_min_n`) und bleibt befundfrei – kein
  Skip-Eintrag mehr

## Lauf 2 – Negativtest DQ-02 (`--rechtsform personengesellschaft`)

**Summen: 6 hoch / 29 mittel / 49 Hinweise | KI-Kandidaten: 22**

Abweichungen gegenüber Lauf 1 (alles Übrige identisch):

- hoch zusätzlich: **DQ-02 (2)** – Namens-Kürzel „GmbH" und
  KSt-Indizien widersprechen der Angabe Personengesellschaft
- mittel: PP-04 entfällt (Privatkonten bei PersG zulässig)
- hinweis zusätzlich: PP-01 (1), PP-02 (1) – Entnahme-Checks aktiv
- Skips: PP-04 (statt PP-01/02/SB-10); BL-05, CO-02, FR-03 unverändert
  (ST-08 aktiv wie in Lauf 1)
- salden.csv/Bilanzblatt schalten auf das PersG-EK-Schema um
  (Kapitalanteile statt § 266-KapG-Gliederung); die Bilanzprobe bleibt
  0,00

## Lauf 3 – Cut-off-Nachlauf CO-02 (`--stapel-folgejahr testdaten/folgejahr`)

Aufruf = Lauf 1 zusätzlich mit `--stapel-folgejahr testdaten/folgejahr`.

**Summen: 4 hoch / 30 mittel / 48 Hinweise | KI-Kandidaten: 23**

Abweichungen gegenüber Lauf 1 (alles Übrige identisch):

- hinweis zusätzlich: **CO-02 (1)** – genau der gesäte Fall
  `ER-2026-015` (Wareneinkauf 6.500,00 EUR am 08.01.2026, Fenster
  01.01.2026–14.01.2026, Quelle `EXTF_Buchungsstapel_2026_Demo.csv`).
  Die übrigen Folgejahres-Zeilen bleiben treffer-frei: EB-Buchung
  (Saldovortrag), Miete Januar (Dauerbuchungs-Muster des Prüfjahres,
  zudem unter `cutoff_min_eur`), Kleinbetrag, Erlösbuchung (CO-02 ist
  aufwandsseitig), Gehälter 28.01. (außerhalb des Fensters)
- KI-Kandidaten 23 (CO-02-Fall kommt hinzu)
- Skips: CO-02 entfällt; PP-01, PP-02, SB-10, BL-05, FR-03 unverändert
  (ST-08 aktiv wie in Lauf 1)

## Standardkonfigurations-Invarianten der v0.2.0-Präzisierungen

- ET-01 prüft netto (`vst_abzugsberechtigt: true`); der gesäte Fall
  (Geschenk 75,00 EUR netto) bleibt genau ein Mittel-Befund.
- US-04: Demodaten enthalten keinen nicht abziehbaren Anteil → weiterhin
  genau ein Mittel-Befund (Existenzfall); die Quotenprüfung
  (`bewirtung_nabz_quote_min`) feuert bei den Demodaten nicht.
- ST-04: `feiertage_zusatz` leer → unverändert ein Hinweis (So 13.07. +
  Feiertag 01.05.).

## Cut-off- und Bilanz-Invarianten der v0.4.0-Überarbeitung

- CO-01 ist erlös-/forderungsseitig und strikt am WJ-Ende aus dem
  DATEV-Header verankert (WJ-Beginn Feld 13 + 12 Monate − 1 Tag; nie
  31.12. unterstellt). Fenster `cutoff_fenster_vor_tage` = 14: der
  gesäte Fall RE2025-113 bleibt der EINZIGE Treffer, der Befundtext
  nennt „18.12.2025–31.12.2025" (die Verbreiterung 5→14 fängt in den
  Demodaten keine weiteren Erlösbuchungen ≥ 5.000 EUR; Bareinnahmen
  liegen unter `cutoff_min_eur`).
- Aufwandsbuchungen vor dem WJ-Ende sind bewusst KEIN CO-01-Fall mehr
  (Spiegelprüfung ist CO-02 im Folgejahr); Gehälter/Dauerbuchungen
  bleiben über den Serien-Filter ausgenommen.
- BL-04 und PP-02 nutzen dasselbe Fenster `cutoff_fenster_vor_tage`
  (Anker WJ-Ende); der gesäte BL-04-Fall (15.06.) und der PP-02-Fall
  (29.–31.12.) verhalten sich unverändert.
- Eigenkapital-Ausweis rechtsformabhängig (salden.csv, Blatt Bilanz,
  Power-BI-Vorlage): KapG-Lauf zeigt A.I 24.000,00 / A.II 30.000,00 /
  A.IV 82.520,00 / A.V +213.433,75 (lt. GuV) / A.VI −6.500,00
  (Privatkonten, PP-04-Fall); Saldenvortrags-Differenz als eigene
  Passivzeile „Z." (+1.000,00, SB-06-Fall). Die Passiva-Tabelle der
  PBI-Bilanzseite summiert damit exakt auf die Bilanzsumme.

## Vorjahres-Invarianten der v0.3.1-Korrektur

- Die Vorjahres-SuSa schließt doppisch auf null: Konto 868
  „Ergebnisvortrag" ist die dynamisch berechnete EK-Gegenwertzeile des
  Generators. Ihr bewusst fehlender EB-Vortrag ist der zweite
  VJ-01-Hinweis (kapitalnah), konsistent zur SB-06-Story.
- `salden.csv` und Blatt „Salden je Konto" führen Vorjahreskonten ohne
  Berichtsjahresbewegung (Demodaten: 868, 4640) mit Buchungen 0 und
  Position nach Vorjahres-Saldenlage; damit sind die Vorjahresspalten
  von Bilanz und GuV vollständig und die Vorjahresbilanz geht exakt auf
  (Kontrolle 0,00 in beiden Jahren).

## Volumen-Invarianten der v0.4.1-Skalierung

Vier Füllströme heben den Stapel auf 1.504 Zeilen (realistische
Kleinst-KapG, Vorgabe ≥ 1.200) und sind konstruktiv befundneutral:

- Ströme: 340 Ausgangsrechnungen Debitor 10010 an 8401 (Automatik
  19 %, Rechnungskreis `FA2025-1001` ff. lückenlos, datumsmonoton) mit
  340 belegtragenden Zahlungseingängen; 160 Wareneingänge 3405 an
  Kreditor 70010 (`WE2025-`) mit 160 beleglosen Bankzahlungen; 170
  Kleingeräte-Direktbuchungen 4985 (BU 9, `WZ2025-`); 120 beleglose
  Bankgebühren 4970.
- Erstziffern der Füllbeträge werden per Restbedarfs-Ziehung gegen das
  Benford-Sollprofil des Gesamtbestands vergeben → ST-08 läuft aktiv
  und befundfrei; Betragsfenster je Strom [3B, 30B) (Spannweite 10:1)
  hält den robusten MAD-z unter ~3 (keine ST-02-Scheinausreißer).
- Zahlungen stets > `doppel_fenster_tage` nach Rechnung (ST-01-neutral),
  alle Füllposten bis 30.12. ausgeglichen (OPOS-/OP-neutral); Beträge
  unter `cutoff_min_eur` (CO-01-neutral) und auf den sachfremd-Konten
  4985/4970 unter `llm_kandidat_min_eur` (KI-Kandidaten bleiben 22);
  beleglose Zahlungen halten die ST-05-Belegfeldquote über 20 %, die
  Debitoren-Belege die RE-Parsequote über 60 %.
- Der gesäte Befundbestand aller drei Läufe ist gegenüber v0.4.0
  unverändert (jeder Fall genau einmal, keine Scheinbefunde).
