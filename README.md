# Jahresabschluss-Agent (DATEV) – Claude-Code-Plugin

Prüft DATEV-Buchungsstapel wie ein erfahrener Abschlussprüfer und liefert
einen strukturierten Excel-Prüfbericht – bereit zur Durchsicht, kein
Textblock. Kernprinzip: **Regeln, die eindeutig sind, gehören in Code, nicht
ins Prompt.** 66 Checks laufen deterministisch in Python, klassifiziert in
vier Prüfebenen (1 technische Integrität, 2 Regelprüfung, 3 Plausibilität,
4 Anomalie) und nach Prüfungstyp ([R] regelbasiert, [P] Plausibilität,
[A] Anomalie, [X] benötigt Zusatzdaten); die KI beurteilt nur die
Kandidaten, die sich nicht in Regeln fassen lassen (sachfremde Buchungen,
Privatveranlassung, Aktivierungs- und Cut-off-Fragen). Prüfungen, die
weitere Datenquellen erfordern, weist der Bericht als solche aus – sie
werden aktiv, sobald die Quelle angeliefert wird.

## Architektur

```
DATEV-Exporte (EXTF/DTVF-CSV)
   Buchungsstapel (Pflicht) · SuSa (optional) · OPOS (optional) · Kontenbeschriftungen (optional)
        │
        ▼
werkzeuge/ja_pruefung.py          deterministische Pipeline (Python, ohne LLM)
   ├─ datev_parser.py             EXTF/DTVF-Parser (Kat. 21/20), SuSa-/OPOS-Leser
   ├─ kontenplan.py               SKR03/SKR04-Erkennung, Kontengruppen, Steuerableitung
   ├─ checks.py / checks_erweitert.py / statistik.py   66 Checks in 4 Ebenen
   └─ excel_report.py             Excel-Prüfbericht (openpyxl, inkl. OPOS-Alterung)
        │
        ├─ Pruefbericht_<Mandant>_<Jahr>.xlsx   (Übersicht, Befunde je Bereich, Salden)
        ├─ befunde.json                         (maschinenlesbar)
        └─ llm_kandidaten.json                  (max. 200 Buchungen für die KI)
        ▼
KI-Schicht (Claude, Skill „ja-pruefung“)        beurteilt NUR die Kandidaten
        │   llm_beurteilung.json
        ▼
werkzeuge/llm_einarbeiten.py                    schreibt Urteile + Summary in den Bericht
```

Vollständige **Abdeckungsmatrix** (Datenintegrität, Journal, Kasse/Bank,
Debitoren, Kreditoren, AV/AfA, Vorräte, sonstige Bilanzkonten,
GuV-Plausibilitäten, USt inkl. Verprobung, Ertragsteuer, Lohn, Cut-off,
Gesellschafter, Stammdaten, Fraud-Indikatoren, Cross-Checks – je
Katalogpunkt mit Status und ggf. benötigter Datenquelle):
[skills/ja-pruefung/references/pruefkatalog.md](skills/ja-pruefung/references/pruefkatalog.md)

## Schnellstart (lokal, ohne Plugin-Installation)

```bash
py werkzeuge/ja_pruefung.py --stapel <Ordner-mit-EXTF-Dateien> --susa susa.csv --opos opos.csv --mandant "Mustermann GmbH"
```

Demo mit synthetischen Daten (alle Fehlerbilder eingebaut):

```bash
py testdaten/erzeuge_testdaten.py
```

```bash
py werkzeuge/ja_pruefung.py --stapel testdaten --susa testdaten/SuSa_2025_Demo.csv --opos testdaten/OPOS_2025_Demo.csv --mandant "Demo GmbH & Co. KG" --ausgabe testdaten/ausgabe
```

Voraussetzungen: Python 3.10+ mit `openpyxl` (`py -m pip install openpyxl`).

## Plugin-Installation

**Claude Desktop / Cowork:** die Datei `dist/jahresabschluss-agent.plugin`
in den Chat ziehen bzw. über die Plugin-Verwaltung hinzufügen. Danach steht
der Skill `/ja-pruefung` zur Verfügung.

**Claude Code (CLI):**

```bash
claude plugin marketplace add "C:\Users\MarlonFranke\Documents\#Claude Code Projects\JA-Agent"
```

```bash
claude plugin install jahresabschluss-agent@ja-agent
```

Kontext-Fußabdruck: Das Plugin lädt pro Sitzung nur die einzeilige
Skill-Beschreibung; Katalog und Werkzeuge werden erst bei Nutzung gelesen.
Empfehlung: nur in den Projekten/Arbeitsbereichen aktivieren, in denen
JA-Prüfungen laufen.

## DATEV-Export (Kanzlei-Anleitung)

1. **Buchungsstapel:** Rechnungswesen → Bestände → Exportieren →
   Buchungsstapel im DATEV-Format; gesamtes Wirtschaftsjahr, EB-Buchungen
   mitnehmen. Mehrere Monatsdateien sind in Ordnung – den Ordner übergeben.
2. **SuSa (empfohlen):** Summen- und Saldenliste als CSV mit Spalten
   `Konto;Saldo` (Soll positiv). Aktiviert Bestandsabgleich und
   USt-/VSt-Verprobung.
3. **OPOS (empfohlen):** OP-Liste als CSV mit Konto, Betrag,
   Belegdatum/Fälligkeit. Aktiviert die Altposten-Prüfung.
4. **Kontenbeschriftungen:** Export Kat. 20 in denselben Ordner legen –
   wird automatisch erkannt, Bericht zeigt dann Kontonamen.

## Konfiguration

`werkzeuge/konten_config.json` enthält alle Parameter (Schwellwerte,
Zeitfenster, GWG-Grenze) und die Kontenbereiche je SKR. Die Zuordnungen sind
DATEV-Standardannahmen und **vor Produktiveinsatz gegen den
Kanzlei-Kontenplan zu prüfen** (v. a. Grund und Boden, Automatikkonten,
uWA-/Verbindlichkeitskonten). Bei individuellen Kontenplänen Kopie der
Config anlegen und mit `--config` übergeben.

## Prüfkatalog (Abdeckungsstand)

Struktur und Klassifikation folgen dem Referenzkatalog
([Prüfkatalog für einen Python-basierten Accounting-Agenten.md](Prüfkatalog%20für%20einen%20Python-basierten%20Accounting-Agenten.md));
die tabellarische Fassung mit Details liegt in
[skills/ja-pruefung/references/pruefkatalog.md](skills/ja-pruefung/references/pruefkatalog.md).

### Legende

- **[R] Rule-based:** objektiv anhand definierter Regeln prüfbar
- **[P] Plausibilität:** Schwellenwert-/Vergleichsprüfung
- **[A] Anomalie:** statistischer oder datengetriebener Auffälligkeitsscore
- **[X] Zusatzdaten:** Prüfung benötigt mehr als den Buchungsstapel

Status: angehakt = umgesetzt (→ `CHECK-ID` bzw. **KI** =
KI-Beurteilungsschicht) · offen = **zusätzliche Prüfung**, wird aktiv,
sobald die mit ➕ genannte Datenquelle angeliefert wird.

### Zielarchitektur: vier Ebenen

| Ebene | Frage |
|---|---|
| 1 – technische Integrität | Sind die Daten vollständig und rechnerisch konsistent? |
| 2 – Regelprüfung | Verstößt ein Sachverhalt gegen eine eindeutige Buchungs-, Bilanzierungs- oder Steuerregel? |
| 3 – Plausibilität | Passt der Sachverhalt zu Schwellen, Zeitreihe, Gegenkonto und wirtschaftlichen Relationen? |
| 4 – Anomalie | Ist der Sachverhalt statistisch/strukturell ungewöhnlich, ohne konkreten Regelverstoß? |

Jeder Befund trägt Ebene und Klasse – ein verdächtig runder Betrag steht
nie auf derselben Stufe wie eine rechnerisch negative Kasse.

### 1. Datenvollständigkeit und technische Integrität

- [x] [R] Soll = Haben (Beleg/Periode/Jahr) → strukturell gewährleistet (DATEV-Einzeilenformat Konto/Gegenkonto)
- [x] [R] Buchungen ohne Konto, Gegenkonto oder Betrag → `DV-01` + Import-Abweisungen `DQ-01`
- [x] [R] Buchungen ohne Belegdatum → `DQ-01`
- [x] [P] Buchungen ohne Belegnummer / ohne Buchungstext → `ST-05`
- [x] [R] ungültige bzw. unbekannte Konten → `DV-03` (mit Kontenbeschriftungen)
- [x] [R] ungültige Steuerschlüssel → `US-03`
- [x] [R] Buchungen außerhalb des Wirtschaftsjahres → `ST-06`
- [ ] [R] Buchungen in nicht vorgesehenen Perioden ➕ GDPdU-Journal (Buchungsdatum)
- [x] [P] Lücken/Sprünge in Rechnungsnummern (Ausgang) → `RE-01` (Eingangsnummern bewusst ausgenommen: fremdvergeben)
- [ ] [R] identische technische Buchungs-IDs ➕ Journal mit Buchungs-IDs
- [x] [R] inkonsistente Buchungssätze (Konto = Gegenkonto) → `DV-01`

**Jahresübernahme**

- [ ] [R] EB-Werte = Schlussbilanz Vorjahr, je Bilanzkonto ➕ Vorjahresdaten
- [x] [R] keine EB-Buchungen auf GuV-Konten → `DV-02`
- [x] [R] Saldenvorträge saldieren auf null → `SB-06`
- [ ] [P] neue Bilanzkonten ohne Anfangsbestand / verschwundene Vorjahreskonten ➕ Vorjahresdaten

### 2. Journal- und Buchungsprüfung

- [x] [R] exakt identische Doppelbuchungen → `ST-01` (hoch bei identischem Beleg)
- [x] [P] wirtschaftlich wahrscheinliche Doppelbuchungen → `ST-01` + KI
- [x] [P] gleicher Betrag + gleicher Partner + gleiches Datum → `ST-01`
- [x] [P] gleiche Rechnungsnummer mehrfach gebucht → `RE-02` (Ausgang), `KR-01` (je Kreditor)
- [x] [P] Buchung und Storno ohne Anlass, Mehrfachstorno → `FR-01`
- [x] [P] ungewöhnlich viele Abschluss-/Nachtragsbuchungen → `GV-01`, `CO-01`
- [x] [P] rückdatierte Buchungen (Indiz über Nummernfolge) → `RE-03`; vollständig ➕ Journal mit Erfassungsdatum
- [ ] [P] großer Abstand Beleg-/Buchungsdatum ➕ Journal
- [ ] [A] Buchungen zu ungewöhnlichen Zeiten / je Benutzer ➕ Journal mit User und Zeitstempel
- [x] [A] ungewöhnliche Konten-Gegenkonten-Kombination, erstmalige Kontierung → `GV-03`
- [x] [A] ungewöhnliche Buchungstexte → **KI** + `ET-02` (regelbasierte Textmuster)
- [x] [P] Buchungen knapp an Freigabegrenzen → `FR-03` (konfigurierbar)
- [x] [A] Aufteilung eines Gesamtbetrags auf Einzelbuchungen → `ST-07`

### 3. Kasse und liquide Mittel

- [x] [R] negativer Kassenbestand zu irgendeinem Zeitpunkt → `SB-01` (taggenauer Verlauf, § 146 AO)
- [x] [R] chronologisch fortgeschriebener Kassenbestand → Verlaufsrechnung in `SB-01`/`SB-07`
- [x] [P] ungewöhnlich hohe Kassenbestände → `SB-07`
- [x] [P] hohe Bareinzahlungen/-entnahmen, sprunghafte Bestandsänderungen → `SB-09`
- [x] [P] ungewöhnlich viele glatte Bargeldbeträge → `SB-10`, `ST-03`
- [ ] [P] nachträgliche Kassenbuchungen ➕ Journal (Erfassungsdatum)
- [x] [P] größere zeitliche Lücken in der Kassenführung → `SB-08`
- [ ] [X] Kassenbuch gegen Finanzbuchhaltung ➕ Kassenbuch-Export
- [ ] [X] Banksaldo/-bewegungen gegen Kontoauszug, ungeklärte Posten, Transfers zwischen eigenen Konten ➕ Bankbewegungen (CAMT/CSV)
- [x] [R] gleiche Zahlung mehrfach verbucht → `ST-01`

### 4. Debitoren und Forderungen

- [x] [R] Debitoren-Hauptbuch = Nebenbuch (OPOS-Summen je Konto) → `OP-05`
- [x] [P] Kreditsalden auf Debitorenkonten → `OP-01`
- [x] [P] überfällige Forderungen → `OP-03`
- [x] [P] OPOS-Altersstruktur 30/60/90/180/365 Tage → Berichtsblatt „OPOS-Alterung"
- [x] [P] sehr alte Kleinstbeträge / sehr alte Gutschriften → `OP-06`
- [ ] [R] ausgeglichene Rechnungen noch offen, doppelte offene Rechnungen ➕ OPOS mit Ausgleichsinformation
- [x] [P] Zahlung ohne korrespondierende Forderung → `OP-01`
- [ ] [P] Teilzahlungsmuster, Zahlungsverhalten je Kunde ➕ Zahlungshistorie/Vorjahr
- [x] [P] Verrechnung zwischen Personenkonten → `OP-04`
- [x] [A] Konzentrationsrisiko einzelner Debitoren → `OP-07`
- [ ] [P] Forderungsanstieg ohne Umsatzentwicklung ➕ Vorjahresdaten
- [ ] [X] Zahlungseingänge nach Stichtag, Mahnstatus, Wertberichtigung vs. Alter, verbundene Unternehmen ➕ Folgeperiode/Mahnwesen/Kontenzuordnung

### 5. Kreditoren und Verbindlichkeiten

- [x] [R] Kreditoren-Hauptbuch = Nebenbuch → `OP-05`
- [x] [P] Sollsalden auf Kreditorenkonten → `OP-02`
- [x] [P] sehr alte Verbindlichkeiten / alte Gutschriften → `OP-03`, `OP-06`
- [x] [R] identische Eingangsrechnung mehrfach erfasst → `ST-01`
- [x] [P] gleiche Rechnungsnummer beim gleichen Kreditor → `KR-01`
- [x] [R] doppelte Zahlungen → `ST-01`; Abgleich gegen Bank ➕ Bankbewegungen
- [x] [P] Zahlung ohne offene Verbindlichkeit → `OP-02`
- [x] [A] ungewöhnliches Kreditorenkonto für Kostenarten → `GV-03`
- [ ] [A] Änderung des Zahlungsprofils, ungewöhnliche Vorauszahlungen, Zahlungen nach Stichtag ➕ Vorjahr/Folgeperiode

### 6. Anlagevermögen und AfA

- [ ] [R/X] Sachkonten, kumulierte AfA, Zu-/Abgänge = Anlagenbuchhaltung ➕ Anlagenspiegel
- [x] [R] Anlagenzugänge ohne AfA (Gesamtbestand) → `AF-01`
- [x] [R] AfA ohne Anlagevermögen → `AF-02`
- [x] [R] AfA auf nicht abnutzbares AV (Grund und Boden) → `AF-03`
- [x] [R] negativer Buchwert → `SB-02`
- [ ] [R] je Wirtschaftsgut: AfA > Restwert, AfA nach Abgang, Nutzungsdauer, AfA-Methode, zeitanteilige AfA ➕ Anlagenspiegel
- [x] [R/P] GWG-/Sammelposten-Grenzen → `AF-04`; Schwellen-Splitting → `ST-07`
- [x] [P] größere Anschaffungen unmittelbar als Aufwand → `AF-05` + **KI**
- [x] [P] laufende Aufwendungen unplausibel aktiviert → **KI** (Kandidaten)
- [ ] [X] außerplanmäßige AfA auf Wertminderungen, Abgang gegen Erlös/Abgangsergebnis ➕ Anlagenspiegel/Belege

### 7. Vorräte und Waren

- [x] [P] Warenaufwand vs. Umsatzentwicklung → Kennzahlen (Material-/Rohertragsquote)
- [x] [P] auffällige Buchungen auf Bestandskonten unmittelbar vor Stichtag → `CO-01`
- [ ] [X] Inventurlisten, Mengendaten, Reichweiten, Niederstwert-Indikatoren ➕ Inventur-/Warenwirtschaftsdaten

### 8. Sonstige Bilanzkonten

- [x] [P] wiederkehrende Zahlungen ohne RAP / RAP aus Vorjahr nicht aufgelöst → `BL-01`
- [ ] [P] ungewöhnlich alte RAP-Positionen, RAP-Veränderungen ➕ Vorjahresdaten
- [x] [P] Vorjahresrückstellung ohne jede Bewegung → `BL-02`
- [ ] [P] jährlich identische Rückstellungen, starke Schwankungen, Abzinsung ➕ Vorjahr/Verträge
- [x] [P] Darlehen ohne Zinsbuchungen → `BL-03`
- [ ] [R/X] Darlehenssaldo gegen Tilgungsplan, Zinsaufwand gegen Zinssatz, Fristigkeiten ➕ Darlehensverträge
- [x] [P] Buchungen unmittelbar auf EK-Konten, unterjährig auf Gewinnvortrag → `BL-04`
- [ ] [R] Vortrag des Vorjahres, Ergebnisverwendung ➕ Vorjahresdaten
- [x] [P] ungewöhnliche Einlagen/Entnahmen, Gesellschafterkonten → `PP-02`, `SB-10`, `GS-01`

### 9. GuV- und Kontenplausibilitäten

- [ ] [P] jedes GuV-Konto gegen Vorjahr/Vorperiode, Vorzeichenwechsel, erstmalig bebucht / plötzlich leer ➕ Vorjahres-SuSa
- [x] [A] Monatsverlauf, ungewöhnliche Monatsspitzen → `GV-01`
- [x] [P] Verhältniskennzahlen (Material-, Personal-, Raum-, Werbe-, Kfz-Quote, Rohertrag) → Kennzahlen-Ausweis; Benchmarking ➕ Vorjahr/Branche
- [x] [A] ungewöhnliche Gegenkonten → `GV-03`
- [x] [A] sachfremde Buchungstexte → **KI**
- [x] [P] außergewöhnlich hohe Einzelbuchungen → `ST-02`
- [x] [P] ungewöhnlich viele glatte Beträge → `ST-03`, `FR-04`
- [x] [P] außergewöhnliche Beträge kurz vor Periodenende → `CO-01`
- [x] [P] starke Gegenbuchungen auf einseitigen Konten, hohe Gutschriften → `GV-02`

### 10. Umsatzsteuer

- [x] [R] Erlös-/Aufwandskonto ↔ Steuerschlüssel plausibel → `US-05`, `US-08`
- [x] [R] Steuerbetrag mathematisch, Steuersatz gegen Schlüssel → `US-06`/`US-07` (Verprobung mit SuSa), Schlüsselkatalog
- [x] [P] Steuerschlüssel je Geschäftspartner verändert → `US-09`
- [x] [R/P] falsches Vorzeichen auf Steuerkonten, Direktbuchungen → `US-02`, `GV-02`
- [ ] [R] Abstimmung gegen UStVA und USt-Jahreserklärung ➕ UStVA-/Erklärungswerte
- [x] [R/P] Vorsteuer auf Konten mit eingeschränktem Abzug → `US-01`
- [x] [P] ungewöhnlich hohe Vorsteuerbeträge → `ST-02`
- [x] [P] Vorsteuer ohne Belegbezug → `US-10`
- [ ] [X] Rechnung vorhanden, Pflichtangaben §§ 14, 14a UStG, Leistungsbezug, zeitlicher Abzug ➕ digitale Belege
- [ ] [R/P/X] Reverse Charge § 13b, EU-Sachverhalte (ig. Erwerb/Lieferung, ZM, Intrastat) ➕ 13b-/EU-Schlüsselkatalog + Stammdaten
- [ ] [P/X] Berichtigungen § 17 (Gutschrift, Skonto, Boni, Uneinbringlichkeit), § 15a, § 14c ➕ Skonto-Auswertung/OPOS-Historie/Belege

### 11. Ertragsteuerliche Auffälligkeiten

- [x] [R] Geschenke über der Abzugsgrenze bzw. auf falschem Konto → `ET-01`, `ET-02`
- [x] [R] Bewirtung ohne nicht abziehbaren Anteil → `US-04`
- [x] [R] Geldbußen/Ordnungsgelder als abziehbar behandelt → `ET-02` (Textmuster)
- [x] [R] Gewerbesteuer als abziehbare Betriebsausgabe → `ET-02` (Textmuster)
- [x] [R] Spenden/Sponsoring auf Werbekonten → `ET-02` (Textmuster)
- [x] [P] private bzw. gesellschaftlich veranlasste Aufwendungen → **KI** + `GS-01`
- [x] [P] hohe Reise-/Fahrzeug-/Repräsentationskosten → Kennzahlen + `ST-02` + **KI**
- [x] [P] mögliche vGA-Sachverhalte (Review-Hinweis) → **KI**
- [x] [P] ungewöhnliche Privatkontenbewegungen → `PP-02`, `SB-10`

### 12. Lohn- und Personalverrechnung

- [x] [R] Lohnaufwand ohne LSt-/SV-Verbindlichkeiten → `PP-03`
- [x] [P] negative Lohn-/Gehaltsaufwendungen → `GV-02`
- [x] [P] Mitarbeiterzahlungen außerhalb üblicher Lohnkonten → `GV-03`
- [ ] [R/X] Lohnjournal gegen FIBU, Verbindlichkeiten gegen Abrechnung, Personalkosten vs. Mitarbeiterentwicklung, Urlaubs-/Bonusrückstellungen ➕ Lohnjournal/Personaldaten

### 13. Periodenabgrenzung und Cut-off

- [x] [P] große Erlös-/Aufwandsbuchungen in den letzten Tagen des Jahres → `CO-01`
- [x] [P] wiederkehrende Jahreskosten/-erlöse ohne Abgrenzung → `BL-01`
- [ ] [P/X] Rechnungsdatum/Buchungsdatum über die Jahresgrenze, Stornos nach Jahresende, verspätete Eingangsrechnungen, Leistungsdatum gegen Periode ➕ Folgeperioden-Stapel/Journal/Belege

### 14. Intercompany und Gesellschafter

- [x] [P] Bewegungen auf Gesellschafterkonten, privat wirkende Aufwendungen mit Gesellschafterbezug → `GS-01` + **KI**
- [ ] [R/X] Spiegelbild-Abstimmungen (Forderung A = Verbindlichkeit B, Zins/Zins, IC-Salden) ➕ Daten der Gegenseite

### 15. Stammdatenprüfung

- [x] [R] identische Kunden/Lieferanten mehrfach angelegt (Bezeichnung) → `SD-01`
- [x] [P] neue/Einmal-Kreditoren mit hohem Volumen → `FR-02`
- [ ] [R/P] IBAN-Dubletten, Adressabgleiche (Lieferant/Mitarbeiter/Kunde), Bankverbindungs-Änderung vor Zahlung, Pflichtfelder ➕ Debitoren-/Kreditorenstammdaten

### 16. Fraud-/Forensic-Indikatoren

Nur Risikosignale, keine Fehlernachweise (Ausweis stets auf Ebene 4).

- [x] [A] auffällig runde Beträge / Endziffern-Häufung → `ST-03`, `FR-04`
- [x] [A] Benford-Analyse als ergänzendes Screening → `ST-08`
- [x] [A] Beträge knapp unter Freigabegrenzen, Aufteilung größerer Beträge → `FR-03`, `ST-07`
- [x] [A] Buchungen an Wochenenden/Feiertagen (Kasse) → `ST-04`
- [x] [A] hohe Stornoquote, Mehrfachstornos → `FR-01`
- [x] [A] Lieferanten mit nur einer großen Transaktion → `FR-02`
- [x] [A] ungewöhnliche Freitexte und Kontierungswege → `GV-03` + **KI**
- [x] [A] außergewöhnliche Buchungen unmittelbar vor Abschluss → `CO-01`
- [ ] [A] User-/Uhrzeit-/IBAN-Muster, Storno unmittelbar nach Stichtag ➕ Journal mit User/Zeit, Stammdaten, Folgeperiode

### 17. Gesamtabschluss und Cross-Checks

- [x] Stapel ↔ Summen- und Saldenliste → `SB-05`
- [x] Umsatzsteuerkonten ↔ rechnerische USt/VSt → `US-06`/`US-07`
- [x] Sachkonten ↔ OPOS-Nebenbuch → `OP-05`
- [x] OPOS ↔ Altersstruktur → Blatt „OPOS-Alterung"
- [ ] Schlussbilanz Vorjahr ↔ EB, Vorjahresvergleiche ➕ Vorjahresdaten
- [ ] Anlagen-/Lohnbuchhaltung, Bank, Kassenbuch, UStVA, ZM, Inventur, Verträge, Intercompany ➕ jeweilige Datenquelle (siehe 20.)

### 18. Kontenspezifische Erwartungslogik

Teilweise umgesetzt über Kontengruppen-Erwartungen in
`werkzeuge/konten_config.json`: erwartetes Vorzeichen (`SB-02`), übliche
Steuerschlüssel dynamisch (`US-05`/`US-08`/`US-09`), Betragsbandbreite
dynamisch (`ST-02`), Buchungsfrequenz (`SB-08`), erlaubte Themen je Konto
(`ET-02`). Ausbaustufe: `erwartungen`-Objekt je Einzelkonto
(Gegenkonten-Whitelist, Monatsverteilung, Vorjahresabweichung).

### 19. Ergebnisstruktur je Treffer

Jeder Befund führt: `check_id`, Prüfbereich, **Ebene (1–4)**, **Klasse
(R/P/A/X)**, Schwere, Konto, Gegenkonto, Datum, Betrag, Beleg,
Buchungstext, Befundtext (erwarteter/tatsächlicher Zustand), empfohlene
Prüfhandlung, Quelle (Datei:Zeile), KI-Kennzeichen sowie leere
**Review-Spalten** (Status, Bearbeiter, Kommentar) im Excel. Die
KI-Schicht ergänzt je Kandidat Urteil, Begründung, Schwere und
**Konfidenz**. Offen: Regelversion, Wesentlichkeitsbezug zur Bilanzsumme.

### 20. Datenquellen

| # | Quelle | Status |
|---|---|---|
| 1 | Buchungsstapel (EXTF/DTVF Kat. 21) | ✔ Pflichtquelle |
| 2 | Summen- und Saldenliste | ✔ optional (`--susa`) → SB-05, US-06/07 |
| 3 | Kontenbeschriftungen (Kat. 20) | ✔ optional, automatisch erkannt → DV-03, SD-01 |
| 4/5 | Debitoren-/Kreditorenstammdaten | ➕ IBAN-/Adress-/Dubletten-Prüfungen |
| 6/7 | OPOS Debitoren/Kreditoren | ✔ optional (`--opos`) → OP-03/05/06, Alterung |
| 8 | Anlagenbuchhaltung | ➕ AfA-Einzelprüfungen je Wirtschaftsgut |
| 9 | Bankbewegungen | ➕ Bank-/Zahlungsabgleich |
| 10 | Kassenbuch | ➕ Kassenbuch-Abstimmung |
| 11 | digitale Belege | ➕ §§ 14/15-Rechnungsprüfung |
| 12 | Steuerschlüssel-Katalog | ✔ `konten_config.json` (erweiterbar) |
| 13 | Kostenstellen | ✔ Feld wird gelesen (Auswertung Ausbaustufe) |
| 14 | Benutzer-/Erfassungsinfos (GDPdU-Journal) | ➕ User-/Zeit-/Rückdatierungs-Checks |
| 15 | Lohnbuchhaltung | ➕ Lohnjournal-Abstimmung |
| 16/17 | UStVA / USt-Jahreswerte | ➕ Erklärungsabgleich |
| 18/19 | Vorjahres-/Mehrjahresdaten | ➕ Zeitreihen-, EB- und Kennzahlenvergleiche |
| 20 | Intercompany-Daten | ➕ Spiegelbild-Abstimmungen |

## Grenzen und Ausbaustufen

- Der Buchungsstapel führt **Bruttoumsätze** mit BU-Schlüsseln; Netto- und
  Steuerwerte werden rechnerisch abgeleitet. Automatische Steuerbuchungen
  erscheinen nicht als Stapelzeilen – Verprobungen laufen deshalb gegen die
  SuSa und sind als Indiz formuliert.
- EB-Werte fließen nur ein, wenn sie im Export enthalten sind; der Bericht
  weist das aus. Prüfungen, deren Datenquelle fehlt, erscheinen als
  „zusätzliche Prüfung" mit der benötigten Quelle – nichts fehlt
  stillschweigend, und 0 Befunde heißt immer „geprüft, ohne Befund".
- Zusätzliche Prüfungen je Datenquelle (Auszug, vollständig im
  Prüfkatalog Kap. 20): Anlagenspiegel → AfA-Einzelprüfungen je
  Wirtschaftsgut; GDPdU-Journal → Rückdatierung, User-/Uhrzeit-Muster;
  Bankbewegungen → Bank-/Zahlungsabgleich; Lohnjournal → Lohn-Abstimmung;
  UStVA-Werte → Erklärungsabgleich; Vorjahres-SuSa → Zeitreihen- und
  EB-Vergleiche; Stammdaten → IBAN-/Adress-Dubletten. Ferner Roadmap:
  DATEV-connect-online-Anbindung statt CSV-Export.

## Datenschutz und Verantwortung

Die Pipeline läuft vollständig lokal. An das Sprachmodell gehen
ausschließlich die Kandidatenzeilen aus `llm_kandidaten.json`
(Buchungstexte, Beträge, Konten) – Mandantendaten also nur in diesem
begrenzten Umfang; Einsatz im Rahmen der kanzleiinternen KI- und
Auftragsverarbeitungsregeln. Der Bericht ist eine Arbeitshilfe und ersetzt
keine fachliche Würdigung durch Berufsträger.
