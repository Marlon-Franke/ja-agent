<!-- KATALOG:REFERENZSTAND:START -->
**Referenzstand:** Version **v0.4.5** des JA-Agenten (= `version` in `.claude-plugin/plugin.json`, Repository-Tag `v0.4.5` mit dem zugehörigen Commit; dieser Block wird von `werkzeuge/katalog_doku.py` generiert und im Build geprüft).
<!-- KATALOG:REFERENZSTAND:END -->

> **Referenzdokument des JA-Agenten** (internes Arbeitsdokument): Soll-Katalog
> der Prüfungen, an dem sich Struktur und Klassifikation des Agenten
> ausrichten. Den Umsetzungsstand je Katalogpunkt weist die Abdeckungsmatrix
> ([skills/ja-pruefung/references/pruefkatalog.md](skills/ja-pruefung/references/pruefkatalog.md))
> aus; Quellen zu Format- und Rechtsbezügen führt die
> [README](README.md) im Abschnitt „Quellen und Referenzen". Kein
> Rechtsrat – Normbezüge vor Anwendung prüfen.
>
> **Fachlicher Rechtsstand:** 18.08.2026 – Normen und Grenzwerte gemäß
> README „Quellen und Referenzen" (jüngste berücksichtigte Änderung:
> KSt-Satzsenkung, BGBl. 2025 I Nr. 161 vom 18.07.2025; Geschenke-Grenze
> 50 EUR seit 2024). **Letzte fachliche Durchsicht des Katalogs:**
> 19.08.2026 (Release 0.4.5: Kanonisierung – jede Checkbox-Zeile dieses
> Katalogs ist in `werkzeuge/soll_katalog.json` genau einem Soll-Punkt mit
> stabiler Soll-ID zugeordnet; die Soll-Klasse der README-/Matrix-Punkte
> ist die Vereinigung der hier vergebenen Tags). Beide Angaben werden von
> Hand gepflegt; die Referenzversion oben wird generiert.
>
> **Bindung an die Strukturdatei:** Der Release-Check
> (`werkzeuge/katalog_doku.py`) prüft, dass jede Checkbox-Zeile
> (`- [ ] [Klasse] Text`) eines Kapitels genau einmal in
> `werkzeuge/soll_katalog.json` referenziert wird und die Klassen
> übereinstimmen. Neue, entfallene oder umformulierte Zeilen hier
> erfordern dieselbe Änderung in der Strukturdatei (`referenz`-Liste des
> betroffenen Soll-Punkts) im selben Arbeitsgang.
>
> **Redaktionelle Klarstellungen zu Kap. 20 (Projektstand):**
> 1. Bilanz und GuV gehen aus dem Buchungsstapel hervor – der Stapel ist
>    die primäre, reichere Quelle. Als eigene Datenquelle sind Bilanz/GuV
>    nur für die Überleitung auf ausgewiesene Positionen relevant
>    (Positions-Zuordnung, Kap. 17).
> 2. Kostenstellen/Kostenträger sind optional, nicht unverzichtbar: Sie
>    erweitern Anomalie-Auswertungen je KOST, sind für die
>    Jahresabschluss-Prüfung aber keine Voraussetzung.
> 3. Vergleichsjahre: Das Minimum ist das Vorjahr (im Agenten über die
>    Vorjahres-SuSa umgesetzt, Checks VJ-01/02); zwei bis fünf Jahre sind
>    die Kür für Zeitreihenanalysen.

## Legende

- **[R] Rule-based:** objektiv anhand definierter Regeln prüfbar
- **[P] Plausibilität:** Schwellenwert-/Vergleichsprüfung
- **[A] Anomalie:** statistischer oder datengetriebener Auffälligkeitsscore
- **[X] Zusatzdaten:** Prüfung benötigt mehr als das Hauptbuch

---

# 1. Datenvollständigkeit und technische Integrität

### Datenbestand
- [ ] [R] Soll = Haben auf Buchungs-/Belegebene
- [ ] [R] Soll = Haben auf Periodenebene
- [ ] [R] Soll = Haben über das gesamte Wirtschaftsjahr
- [ ] [R] Buchungen ohne Konto
- [ ] [R] Buchungen ohne Gegenkonto
- [ ] [R] Buchungen ohne Betrag
- [ ] [R] Buchungen ohne Buchungsdatum
- [ ] [R] Buchungen ohne Belegdatum
- [ ] [R] Buchungen ohne Belegnummer
- [ ] [P] Buchungen ohne Buchungstext
- [ ] [R] ungültige bzw. unbekannte Konten
- [ ] [R] ungültige Steuerschlüssel
- [ ] [R] Buchungen außerhalb des Wirtschaftsjahres
- [ ] [R] Buchungen in nicht vorgesehenen Perioden
- [ ] [P] Lücken oder Sprünge in Beleg-/Buchungsnummern
- [ ] [R] identische technische Buchungs-IDs
- [ ] [R] inkonsistente Datensätze innerhalb desselben Buchungssatzes

### Jahresübernahme
- [ ] [R] Eröffnungsbilanzwerte = Schlussbilanzwerte des Vorjahres
- [ ] [R] EB-Werte je Bilanzkonto abstimmen
- [ ] [R] keine EB-Buchungen auf GuV-Konten
- [ ] [P] neue Bilanzkonten ohne nachvollziehbaren Anfangsbestand
- [ ] [P] verschwundene Vorjahreskonten mit Restbestand

Die Bilanzidentität zwischen Schlussbilanz und Eröffnungsbilanz gehört ausdrücklich zu den Bewertungsgrundsätzen des § 252 Abs. 1 Nr. 1 HGB.

---

# 2. Journal- und Buchungsprüfung

- [ ] [R] exakt identische Doppelbuchungen
- [ ] [P] wirtschaftlich wahrscheinliche Doppelbuchungen trotz unterschiedlicher Buchungs-ID
- [ ] [P] gleicher Betrag + gleicher Kreditor/Debitor + gleiches Rechnungsdatum
- [ ] [P] gleiche Rechnungsnummer mehrfach gebucht
- [ ] [P] gleicher Buchungstext/Betrag in sehr kurzem Zeitraum
- [ ] [P] Buchung und Storno ohne erkennbaren Anlass
- [ ] [P] mehrfaches Storno und erneute Einbuchung desselben Sachverhalts
- [ ] [P] ungewöhnlich viele manuelle Umbuchungen
- [ ] [P] ungewöhnlich viele Abschluss-/Nachtragsbuchungen
- [ ] [P] rückdatierte Buchungen
- [ ] [P] großer Abstand zwischen Beleg- und Buchungsdatum
- [ ] [A] Buchungen an ungewöhnlichen Tagen oder Uhrzeiten, soweit Zeitstempel vorhanden
- [ ] [A] ungewöhnliche Buchungsaktivität einzelner Benutzer
- [ ] [A] ungewöhnliche Konten-Gegenkonten-Kombination
- [ ] [A] erstmalig auftretende Kontierung
- [ ] [A] ungewöhnliche Buchungstexte
- [ ] [A] ungewöhnliche Buchungsfrequenzen
- [ ] [P] Buchungen knapp oberhalb/unterhalb definierter Freigabegrenzen
- [ ] [A] auffällige Aufteilung eines Gesamtbetrags auf mehrere Einzelbuchungen

---

# 3. Kasse und liquide Mittel

### Kasse
- [ ] [R] negativer Kassenbestand zu irgendeinem Zeitpunkt
- [ ] [R] chronologisch fortgeschriebener Kassenbestand
- [ ] [P] ungewöhnlich hohe Kassenbestände
- [ ] [P] ungewöhnlich hohe Bareinzahlungen
- [ ] [P] ungewöhnlich hohe Barentnahmen
- [ ] [P] sprunghafte Kassenbestandsänderungen
- [ ] [P] ungewöhnlich viele glatte Bargeldbeträge
- [ ] [P] nachträgliche Kassenbuchungen
- [ ] [P] größere zeitliche Lücken in der Kassenführung
- [ ] [X] Kassenbuch gegen Finanzbuchhaltung abstimmen

Kasseneinnahmen und Kassenausgaben sind nach § 146 Abs. 1 AO täglich festzuhalten; negative rechnerische Kassenbestände sind deshalb ein besonders aussagekräftiger Plausibilitätstreffer.

### Bank
- [ ] [X] Banksaldo Finanzbuchhaltung gegen Kontoauszug
- [ ] [X] Bankbewegungen gegen Buchungen vollständig matchen
- [ ] [P] lange ungeklärte Bankbuchungen
- [ ] [P] ungewöhnliche Barabhebungen
- [ ] [P] Überweisungen auf ungewöhnliche Gegenkonten
- [ ] [P] ungewöhnliche Geldtransfers zwischen eigenen Konten
- [ ] [R] gleiche Zahlung mehrfach verbucht
- [ ] [X] gleiche Banktransaktion mehreren Rechnungen zugeordnet

---

# 4. Debitoren und Forderungen

- [ ] [R] Debitoren-Hauptbuch = Debitoren-Nebenbuch
- [ ] [P] Kreditsalden auf Debitorenkonten
- [ ] [P] ungewöhnlich hohe Forderungssalden
- [ ] [P] lange überfällige Forderungen
- [ ] [P] OPOS-Altersstruktur: 30/60/90/180/365 Tage
- [ ] [P] sehr alte Kleinstbeträge
- [ ] [P] sehr alte Gutschriften
- [ ] [R] ausgeglichene Rechnungen noch als offen
- [ ] [R] doppelte offene Rechnungen
- [ ] [P] Zahlung ohne korrespondierende Forderung
- [ ] [P] Rechnung ohne Zahlung trotz ungewöhnlich langen Zeitraums
- [ ] [P] ungewöhnlich viele Teilzahlungen
- [ ] [P] ungewöhnliche Verrechnung zwischen Kunden
- [ ] [A] Forderungen deutlich außerhalb des normalen Zahlungsverhaltens eines Kunden
- [ ] [A] Konzentrationsrisiko einzelner Debitoren
- [ ] [P] Forderungsanstieg ohne entsprechende Umsatzentwicklung
- [ ] [X] Zahlungseingänge nach Bilanzstichtag zur Werthaltigkeitsprüfung
- [ ] [X] Mahnstatus gegen OPOS
- [ ] [X] Wertberichtigungen gegen Altersstruktur
- [ ] [X] Forderungen gegen verbundene Unternehmen abstimmen

---

# 5. Kreditoren und Verbindlichkeiten

- [ ] [R] Kreditoren-Hauptbuch = Kreditoren-Nebenbuch
- [ ] [P] Sollsalden auf Kreditorenkonten
- [ ] [P] ungewöhnlich hohe Verbindlichkeiten
- [ ] [P] sehr alte offene Verbindlichkeiten
- [ ] [P] alte Kreditorengutschriften
- [ ] [R] identische Eingangsrechnung mehrfach erfasst
- [ ] [P] gleiche Rechnungsnummer bei gleichem Kreditor
- [ ] [P] gleicher Betrag/Rechnungsdatum/Kreditor mit abweichender Rechnungsnummer
- [ ] [R/X] doppelte Zahlungen
- [ ] [P] Zahlung ohne offene Verbindlichkeit
- [ ] [P] ungewöhnliche Vorauszahlungen
- [ ] [P] ungewöhnlich viele manuelle Kreditorenbuchungen
- [ ] [A] ungewöhnliches Kreditorenkonto für bestimmte Kostenarten
- [ ] [A] erhebliche Änderung des Zahlungsprofils eines Lieferanten
- [ ] [X] Verbindlichkeiten gegen Zahlungen nach Bilanzstichtag
- [ ] [X] Verbindlichkeiten gegenüber verbundenen Unternehmen abstimmen

---

# 6. Anlagevermögen und AfA

### Abstimmung
- [ ] [R/X] Sachkonten Anlagevermögen = Anlagenbuchhaltung
- [ ] [R/X] kumulierte AfA = Anlagenbuchhaltung
- [ ] [R/X] Anlagenzugänge Hauptbuch = Anlagenzugänge Nebenbuch
- [ ] [R/X] Anlagenabgänge Hauptbuch = Anlagenabgänge Nebenbuch

### AfA
- [ ] [R] Wirtschaftsgut vorhanden, aber keine AfA
- [ ] [R] AfA auf vollständig abgegangenes Wirtschaftsgut
- [ ] [R] AfA höher als abschreibbarer Restwert
- [ ] [R] negativer Buchwert
- [ ] [R] Restbuchwert trotz rechnerisch vollständig abgelaufener Nutzungsdauer
- [ ] [R] AfA vor Anschaffungs-/Herstellungsdatum
- [ ] [R] AfA nach Abgang
- [ ] [R] unterjährige zeitanteilige AfA rechnerisch prüfen
- [ ] [R/P] verwendete Nutzungsdauer gegen hinterlegte Soll-Nutzungsdauer
- [ ] [R] AfA-Methode gegen Anlagenstammdaten
- [ ] [P] außergewöhnlich hohe/geringe AfA
- [ ] [P] erhebliche Änderung der AfA gegenüber Vorjahr
- [ ] [P] Anlagenzugang ohne korrespondierende Kreditoren-/Bankbuchung
- [ ] [P] Investitionskonto mit ungewöhnlich vielen Kleinstbeträgen
- [ ] [P] größere Anschaffungen unmittelbar als Aufwand gebucht
- [ ] [P] mögliche aktivierungspflichtige Anschaffungen auf Reparatur-/Instandhaltungskonten
- [ ] [P] mögliche laufende Aufwendungen unplausibel aktiviert
- [ ] [R/P] GWG-/Sammelpostenbehandlung nach hinterlegten steuerlichen Parametern
- [ ] [X] außerplanmäßige Abschreibungen auf dokumentierte Wertminderungen
- [ ] [X] Anlagenabgang gegen Verkaufserlös und Abgangsergebnis

Planmäßige Abschreibungen ergeben sich handelsrechtlich insbesondere aus § 253 Abs. 3 HGB und steuerrechtlich aus § 7 EStG; steuerliche Bewertungs- und GWG-Regeln sind insbesondere in § 6 EStG geregelt.

---

# 7. Vorräte und Waren

- [ ] [R/X] Vorratskonten gegen Inventurlisten
- [ ] [P] ungewöhnlich starke Bestandsänderung
- [ ] [P] negativer Warenbestand, soweit Mengendaten vorhanden
- [ ] [P] Lagerbestand ohne Bewegungen über längere Zeit
- [ ] [A] ungewöhnlich langsam drehende Artikel
- [ ] [A] ungewöhnlich hohe Reichweiten
- [ ] [P] Warenaufwand ohne korrespondierende Umsatzentwicklung
- [ ] [P] Umsatzentwicklung ohne korrespondierende Warenbewegung
- [ ] [P] auffällige Buchungen auf Bestandskonten unmittelbar vor Stichtag
- [ ] [X] Inventurdifferenzen
- [ ] [X] Niederstwert-/Wertberichtigungsindikatoren

Für Umlaufvermögen enthält § 253 Abs. 4 HGB das handelsrechtliche Niederstwertprinzip.

---

# 8. Sonstige Bilanzkonten

### Rechnungsabgrenzung
- [ ] [P] regelmäßig wiederkehrende Zahlungen ohne RAP
- [ ] [P] Versicherungen, Mieten, Wartungen etc. über den Stichtag hinweg
- [ ] [R] RAP aus Vorjahr nicht aufgelöst
- [ ] [P] ungewöhnlich alte RAP-Positionen
- [ ] [P] erhebliche RAP-Veränderungen ohne Geschäftsentwicklung

### Rückstellungen
- [ ] [P] bestehende Vorjahresrückstellung ohne Bewegung
- [ ] [P] jährlich identische Rückstellungsbeträge
- [ ] [P] Rückstellungsauflösung ohne entsprechenden Sachverhalt
- [ ] [P] Aufwand mit Rückstellungscharakter direkt als Verbindlichkeit oder Aufwand behandelt
- [ ] [P] starke Schwankung einzelner Rückstellungen
- [ ] [X] langfristige Rückstellungen hinsichtlich Abzinsung

### Darlehen
- [ ] [R/X] Darlehenssaldo gegen Tilgungsplan
- [ ] [R/X] Zinsaufwand gegen Zinssatz und Saldo
- [ ] [P] Tilgung auf Zinskonto bzw. Zins auf Darlehenskonto
- [ ] [P] Darlehen ohne Zinsbuchungen
- [ ] [P] ungewöhnliche Gesellschafterdarlehen
- [ ] [X] Laufzeiten und Fristigkeiten

### Eigenkapital
- [ ] [R] Vortrag des Vorjahres prüfen
- [ ] [R/X] Ergebnisverwendung rechnerisch prüfen
- [ ] [P] Buchungen unmittelbar auf Eigenkapitalkonten
- [ ] [P] unterjährige Buchungen auf Gewinnvortrag
- [ ] [P] ungewöhnliche Einlagen/Entnahmen
- [ ] [P] Gesellschafterkonten mit ungewöhnlichen Salden

Die Vollständigkeit der Bilanz einschließlich Vermögensgegenständen, Schulden und Rechnungsabgrenzungsposten folgt grundsätzlich aus § 246 Abs. 1 HGB.

---

# 9. GuV- und Kontenplausibilitäten

### Zeitreihen
- [ ] [P] jedes GuV-Konto gegen Vorjahr
- [ ] [P] jedes GuV-Konto gegen Vorperiode
- [ ] [P] Monatsverlauf jedes wesentlichen Kontos
- [ ] [A] ungewöhnliche Monatsspitzen
- [ ] [A] ungewöhnliche saisonale Abweichungen
- [ ] [P] Konto erstmalig mit wesentlichem Saldo
- [ ] [P] Konto plötzlich ohne Saldo
- [ ] [P] Vorzeichenwechsel gegenüber Vorjahr
- [ ] [P] ungewöhnlich starke absolute Veränderung
- [ ] [P] ungewöhnlich starke relative Veränderung

### Verhältniskennzahlen
- [ ] [P] Materialaufwand/Umsatz
- [ ] [P] Personalaufwand/Umsatz
- [ ] [P] Raumkosten/Umsatz
- [ ] [P] Werbekosten/Umsatz
- [ ] [P] Fahrzeugkosten/Umsatz
- [ ] [P] Fremdleistungen/Umsatz
- [ ] [P] Abschreibungen/Anlagevermögen
- [ ] [P] Zinsaufwand/Finanzverbindlichkeiten
- [ ] [P] Forderungen/Umsatz
- [ ] [P] Verbindlichkeiten/Materialaufwand
- [ ] [P] Rohertrag/Rohmarge
- [ ] [P] Umsatz pro Mitarbeiter, wenn Mitarbeiterzahl vorhanden

### Sachkontenanalyse
- [ ] [A] ungewöhnliche Gegenkonten
- [ ] [A] sachfremde Buchungstexte
- [ ] [A] ungewöhnliche Geschäftspartner
- [ ] [P] außergewöhnlich hohe Einzelbuchungen
- [ ] [P] ungewöhnlich viele Kleinstbuchungen
- [ ] [P] ungewöhnlich viele glatte Beträge
- [ ] [P] außergewöhnliche Beträge kurz vor Periodenende
- [ ] [P] außerordentlich hohe Gutschriften
- [ ] [P] starke Gegenbuchungen auf normalerweise einseitigen Konten

---

# 10. Umsatzsteuer

## Steuerlogik

- [ ] [R] Erlöskonto ↔ Steuerschlüssel plausibel
- [ ] [R] Aufwandskonto ↔ Vorsteuerschlüssel plausibel
- [ ] [R] steuerpflichtiges Erlöskonto ohne Umsatzsteuer
- [ ] [R] steuerfreies Erlöskonto mit Umsatzsteuer
- [ ] [R] Vorsteuerkonto ohne korrespondierende Bemessungsgrundlage
- [ ] [R] Steuerbetrag mathematisch gegen Bemessungsgrundlage prüfen
- [ ] [R] Steuersatz gegen verwendeten Steuerschlüssel
- [ ] [P] ungewöhnlicher Steuerschlüssel für bestimmtes Sachkonto
- [ ] [P] Steuerschlüssel gegenüber üblicher Behandlung desselben Lieferanten/Kunden verändert
- [ ] [R/P] Buchung mit falschem Vorzeichen auf Umsatz-/Vorsteuerkonten
- [ ] [R] Umsatzsteuerkonten gegen Umsatzsteuer-Voranmeldung abstimmen
- [ ] [R] Jahreswerte gegen Umsatzsteuer-Jahreserklärung abstimmen

## Vorsteuer

- [ ] [R/P] Vorsteuer auf Konten mit typischerweise eingeschränktem Abzug
- [ ] [P] ungewöhnlich hoher Vorsteuerbetrag
- [ ] [P] Vorsteuer ohne Kreditor bzw. Belegbezug
- [ ] [X] Rechnung vorhanden
- [ ] [X] Rechnungsangaben nach §§ 14, 14a UStG
- [ ] [X] Leistungsempfänger entspricht Unternehmen
- [ ] [X] Leistungsbezug für das Unternehmen
- [ ] [X] Leistungs-/Rechnungsdatum plausibel
- [ ] [X] Vorsteuerabzug zeitlich zutreffend

Der Vorsteuerabzug richtet sich insbesondere nach § 15 UStG und setzt in den dort geregelten Fällen eine Rechnung nach §§ 14, 14a UStG voraus.

## Reverse Charge

- [ ] [R/P] ausländischer Kreditor + Dienstleistung ohne §-13b-Schlüssel
- [ ] [R/P] §-13b-Steuerschlüssel bei untypischem Sachverhalt
- [ ] [R] Umsatzsteuer und korrespondierende Vorsteuer betragsmäßig abstimmen
- [ ] [R] Bemessungsgrundlage gegen Steuerberechnung
- [ ] [P] §-13b-Sachverhalte ohne korrespondierende Steuerbuchung

Rechtsgrundlage ist § 13b UStG.

## EU-Sachverhalte

- [ ] [P/X] EU-Lieferant + Warenbezug ↔ innergemeinschaftlicher Erwerb
- [ ] [P/X] EU-Lieferant + Dienstleistung ↔ Reverse Charge
- [ ] [P/X] EU-Kunde + Warenlieferung ↔ innergemeinschaftliche Lieferung
- [ ] [P/X] EU-Kunde + B2B-Dienstleistung ↔ Leistungsortprüfung
- [ ] [X] USt-IdNr.-Daten
- [ ] [X] Zusammenfassende Meldung gegen Buchhaltung
- [ ] [X] Intrastat gegen Warenbewegungen, soweit einschlägig

## Berichtigungen

- [ ] [P] Gutschrift ohne Umsatzsteuerkorrektur
- [ ] [P] Skonto ohne entsprechende Steuerkorrektur
- [ ] [P] Boni/Rückvergütungen ohne Steuerkorrektur
- [ ] [P/X] uneinbringliche Forderungen ohne §-17-Berichtigung
- [ ] [P/X] nachträgliche Zahlung nach §-17-Berichtigung
- [ ] [X] Änderungen der Nutzung von Investitionsgütern hinsichtlich § 15a UStG

Änderungen der Bemessungsgrundlage und Uneinbringlichkeit werden insbesondere durch § 17 UStG geregelt; Nutzungsänderungen bei Vorsteuerberichtigungsobjekten durch § 15a UStG.

## Unrichtiger Steuerausweis

- [ ] [X] ausgewiesener Steuersatz ≠ gesetzlich geschuldeter Steuersatz
- [ ] [X] Umsatzsteuer auf eigentlich steuerfreien Sachverhalten
- [ ] [X] Umsatzsteuerausweis durch hierzu nicht berechtigte Rechnungsaussteller

Hier besteht insbesondere ein Risiko nach § 14c UStG.

---

# 11. Ertragsteuerliche Auffälligkeiten

- [ ] [P] Geschenke auf falschem Konto
- [ ] [P] Bewirtungsaufwendungen mit unplausibler steuerlicher Behandlung
- [ ] [P] Geldbußen/Ordnungsgelder als abzugsfähiger Aufwand behandelt
- [ ] [P] Gewerbesteuer als abzugsfähige Betriebsausgabe behandelt
- [ ] [P] private bzw. gesellschaftlich veranlasste Aufwendungen auf Betriebsausgabenkonten
- [ ] [P] außergewöhnlich hohe Reisekosten
- [ ] [P] außergewöhnlich hohe Fahrzeugkosten
- [ ] [P] außergewöhnlich hohe Repräsentationskosten
- [ ] [P] Spenden/Sponsoring auf gewöhnlichen Werbekonten
- [ ] [P] Gesellschafteraufwendungen auf allgemeinen Sachkonten
- [ ] [P] mögliche verdeckte Gewinnausschüttungs-Sachverhalte lediglich als Review-Hinweis
- [ ] [P] nicht abziehbare Betriebsausgaben nicht getrennt erfasst
- [ ] [P] ungewöhnliche Privatkontenbewegungen

Insbesondere § 4 Abs. 5 und 5b EStG enthält zahlreiche Abzugsverbote bzw. -beschränkungen; § 4 Abs. 7 EStG verlangt für bestimmte Aufwendungen eine getrennte Aufzeichnung.

---

# 12. Lohn- und Personalverrechnung

Soweit entsprechende Daten verfügbar sind:

- [ ] [R/X] Lohnjournal gegen Finanzbuchhaltung
- [ ] [R/X] Lohnsteuerverbindlichkeiten gegen Lohnabrechnung
- [ ] [R/X] Sozialversicherungsverbindlichkeiten gegen Abrechnung
- [ ] [R/X] Nettolohnverbindlichkeiten gegen Zahlungen
- [ ] [P] ungewöhnliche manuelle Personalbuchungen
- [ ] [P] erhebliche Veränderung der Personalkosten
- [ ] [P] Personalkosten ohne entsprechende Mitarbeiterentwicklung
- [ ] [P] Einmalzahlungen/Ausreißer
- [ ] [P] negative Lohn-/Gehaltsaufwendungen
- [ ] [P] Mitarbeiterzahlungen außerhalb der üblichen Lohnkonten
- [ ] [P] Zahlungen an ehemalige Mitarbeiter
- [ ] [X] Rückstellungen für Urlaub/Boni etc.

---

# 13. Periodenabgrenzung und Cut-off

- [ ] [P] Rechnungsdatum Dezember, Buchungsdatum Januar
- [ ] [P] Rechnungsdatum Januar, Buchungsdatum Dezember
- [ ] [P] große Erlösbuchungen in den letzten Tagen des Jahres
- [ ] [P] große Erlösstornos unmittelbar nach Jahresende
- [ ] [P] große Aufwandsbuchungen unmittelbar nach Jahresende
- [ ] [P] ungewöhnliche Gutschriften unmittelbar nach Jahresende
- [ ] [X] Leistungsdatum gegen Buchungsperiode
- [ ] [X] Wareneingang gegen Eingangsrechnung
- [ ] [X] Ausgangsrechnung gegen Liefer-/Leistungsdatum
- [ ] [P] wiederkehrende Jahreskosten ohne Abgrenzung
- [ ] [P] wiederkehrende Jahreserlöse ohne Abgrenzung
- [ ] [P] verspätete Eingangsrechnungen mit Vorjahresbezug
- [ ] [P] ungewöhnlich viele Abschlussbuchungen nach Periodenschluss

---

# 14. Intercompany und Gesellschafter

- [ ] [R/X] Forderung Gesellschaft A = Verbindlichkeit Gesellschaft B
- [ ] [R/X] Intercompany-Umsatz A = Intercompany-Aufwand B
- [ ] [R/X] Darlehenssalden konzernintern abstimmen
- [ ] [R/X] Zinsaufwand und Zinsertrag spiegelbildlich abstimmen
- [ ] [P] erhebliche ungeklärte Intercompany-Differenzen
- [ ] [P] Buchungen auf Gesellschafterkonten ohne eindeutigen Gegenposten
- [ ] [P] ungewöhnliche Zahlungen an Gesellschafter
- [ ] [P] ungewöhnliche Forderungen gegen Gesellschafter
- [ ] [P] ungewöhnliche Verbindlichkeiten gegenüber Gesellschaftern
- [ ] [P] privat wirkende Aufwendungen mit Gesellschafterbezug

---

# 15. Stammdatenprüfung

## Kreditoren/Debitoren

- [ ] [R] identische Lieferanten mehrfach angelegt
- [ ] [R] identische Kunden mehrfach angelegt
- [ ] [P] nahezu identische Namen/Adressen
- [ ] [R] gleiche IBAN bei mehreren Lieferanten
- [ ] [P] gleiche Anschrift bei Lieferant und Mitarbeiter
- [ ] [P] gleiche Bankverbindung bei Lieferant und Mitarbeiter
- [ ] [P] gleiche Bankverbindung bei Lieferant und Kunde
- [ ] [P] kürzlich geänderte Bankverbindung vor hoher Zahlung
- [ ] [P] neue Kreditoren mit unmittelbar hohem Zahlungsvolumen
- [ ] [P] lange inaktive Kreditoren plötzlich wieder verwendet
- [ ] [P] ungewöhnlich häufig geänderte Stammdaten
- [ ] [R] fehlende Pflichtfelder nach internem Stammdatenstandard

---

# 16. Fraud-/Forensic-Indikatoren

Diese Prüfungen dürfen **nicht als Fehlernachweis**, sondern nur als Risikosignal behandelt werden.

- [ ] [A] auffällig runde Beträge
- [ ] [A] auffällige Häufung bestimmter Endziffern
- [ ] [A] Benford-Analyse als ergänzendes Screening
- [ ] [A] wiederkehrende knapp unterhalb von Freigabegrenzen liegende Beträge
- [ ] [A] Aufteilung größerer Beträge
- [ ] [A] ungewöhnliche Kombination Mitarbeiter/Lieferant
- [ ] [A] ungewöhnliche Kombination Benutzer/Konto
- [ ] [A] Buchungen außerhalb typischer Geschäftszeiten
- [ ] [A] Buchungen an Wochenenden/Feiertagen
- [ ] [A] ungewöhnlich hohe manuelle Buchungsquote
- [ ] [A] außergewöhnlich hohe Stornoquote
- [ ] [A] außergewöhnlich viele Buchungen eines einzelnen Users
- [ ] [A] neue Lieferanten kurz vor großen Zahlungen
- [ ] [A] Lieferanten mit nur einer einzigen großen Transaktion
- [ ] [A] ungewöhnliche Freitexte
- [ ] [A] ungewöhnliche Kontierungswege
- [ ] [A] Zahlung an bislang unbekannte IBAN
- [ ] [A] Änderung Lieferanten-IBAN kurz vor Zahlung
- [ ] [A] gleiche IBAN bei mehreren wirtschaftlich unabhängigen Geschäftspartnern
- [ ] [A] außergewöhnliche Buchungen unmittelbar vor Abschluss
- [ ] [A] Storno unmittelbar nach Stichtag

---

# 17. Gesamtabschluss und Cross-Checks

Der eigentliche Mehrwert entsteht aus **Querverprobungen**, nicht aus isolierter Kontenprüfung.

- [ ] Hauptbuch ↔ Summen- und Saldenliste
- [ ] Hauptbuch ↔ Bilanz/GuV
- [ ] Schlussbilanz Vorjahr ↔ Eröffnungsbilanz
- [ ] Sachkonten ↔ Debitoren-Nebenbuch
- [ ] Sachkonten ↔ Kreditoren-Nebenbuch
- [ ] Sachkonten ↔ Anlagenbuchhaltung
- [ ] Sachkonten ↔ Lohnbuchhaltung
- [ ] Sachkonten ↔ Bank
- [ ] Sachkonten ↔ Kasse
- [ ] Umsatzsteuerkonten ↔ UStVA
- [ ] Umsatzsteuerkonten ↔ USt-Jahreserklärung
- [ ] EU-Umsätze ↔ ZM
- [ ] Warenbestand ↔ Inventur
- [ ] Darlehen ↔ Verträge/Tilgungspläne
- [ ] Forderungen ↔ Zahlungseingänge nach Stichtag
- [ ] Verbindlichkeiten ↔ Zahlungen nach Stichtag
- [ ] Intercompany A ↔ Intercompany B
- [ ] Ergebnis Finanzbuchhaltung ↔ Jahresabschluss
- [ ] Kontenzuordnung ↔ Bilanz-/GuV-Position
- [ ] Vorjahreswerte ↔ aktuelle Vergleichswerte

---

# 18. Kontenspezifische Erwartungslogik

Zusätzlich sollte **jedes Konto einen eigenen Erwartungsvektor** erhalten:

- erwartetes Vorzeichen
- erlaubte Gegenkonten
- übliche Steuerschlüssel
- übliche Geschäftspartner
- typische Buchungstexte
- erwartete Betragsbandbreite
- typische Buchungsfrequenz
- typische Monatsverteilung
- erwartetes Verhältnis zu anderen Konten
- zulässige manuelle Buchungen
- zulässige Abschlussbuchungen
- übliche Vorjahresabweichung
- besondere steuerliche Risiken
- Dokumentationsanforderungen

Beispiel:

**Konto Kasse**

`expected_sign >= 0`

`frequency = daily`

`tax_keys = none/direct transaction dependent`

`risk_rules = negative balance | backdating | round amounts | large cash movement`

**Konto Abschreibungen**

`expected_sign = debit`

`counter_accounts = accumulated_depreciation`

`relationship = asset_register`

`risk_rules = missing_asset | excessive_AfA | post_disposal_AfA | unusual_change`

Damit wird aus einem allgemeinen Anomalie-Agenten tatsächlich ein **digitalisierter Prüfer-Katalog**.

---

# 19. Ergebnisstruktur des Skripts

Jeder Treffer sollte mindestens enthalten:

**Prüfung**
- eindeutige `check_id`
- Prüfbereich
- Prüfschritt
- Regelversion

**Fundstelle**
- Wirtschaftsjahr
- Periode
- Konto
- Gegenkonto
- Buchungsnummer
- Belegnummer
- Buchungsdatum
- Belegdatum
- Geschäftspartner
- Betrag
- Steuerschlüssel
- Buchungstext

**Bewertung**
- Treffergrund
- erwarteter Zustand
- tatsächlicher Zustand
- absolute Abweichung
- relative Abweichung
- Risikoklasse
- Confidence Score
- Regelprüfung / Plausibilität / Anomalie
- Wesentlichkeit

**Review**
- vorgeschlagene Prüfhandlung
- benötigte Zusatzunterlagen
- Bearbeitungsstatus
- Reviewer
- Kommentar
- Ergebnis
- ggf. Korrekturvorschlag

---

# 20. Unverzichtbare Datenquellen

Für einen wirklich leistungsfähigen Agenten reichen **Bilanz und GuV oder selbst die Buchungsstapel allein nicht aus**.

Ideal sind mindestens:

1. Buchungsjournal
2. Sachkonten
3. Kontenstammdaten
4. Debitorenstammdaten
5. Kreditorenstammdaten
6. OPOS Debitoren
7. OPOS Kreditoren
8. Anlagenbuchhaltung
9. Bankbewegungen
10. Kassenbewegungen
11. digitale Belege/Rechnungsdaten
12. Steuerschlüssel
13. Kostenstellen/Kostenträger
14. Benutzer-/Buchungsinformationen
15. Lohnbuchhaltungs-Summen
16. Umsatzsteuer-Voranmeldungen
17. Umsatzsteuer-Jahreswerte
18. Vorjahresdaten
19. idealerweise zwei bis fünf historische Vergleichsjahre
20. gegebenenfalls Intercompany-Daten

---

## Zielarchitektur

Das Python-System sollte daher nicht einfach fragen:

> „Ist diese Buchung ungewöhnlich?“

sondern vier Ebenen nacheinander abarbeiten:

**Ebene 1 – technische Integrität**  
Sind Daten vollständig und rechnerisch konsistent?

**Ebene 2 – Regelprüfung**  
Verstößt ein Sachverhalt gegen eine eindeutig definierbare Buchungs-, Bilanzierungs- oder Steuerregel?

**Ebene 3 – Plausibilitätsprüfung**  
Passt der Sachverhalt zu Vorjahr, Zeitreihe, Gegenkonto, Geschäftspartner und wirtschaftlichen Relationen?

**Ebene 4 – Anomalieerkennung**  
Ist der Sachverhalt statistisch oder strukturell ungewöhnlich, obwohl kein konkreter Regelverstoß festgestellt werden kann?

Erst diese Trennung verhindert, dass ein „verdächtig runder Betrag“ auf derselben Ebene behandelt wird wie eine **rechnerisch negative Kasse oder eine objektiv fehlerhafte AfA**.
