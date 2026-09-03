# Prüfkatalog Jahresabschluss-Agent – Abdeckungsmatrix

Struktur und Klassifikation folgen dem Referenzkatalog
(`Prüfkatalog für einen Python-basierten Accounting-Agenten.md`).

Kanonische Quelle der Soll-Katalogpunkte ist `werkzeuge/soll_katalog.json`:
je Punkt eine stabile **Soll-ID** (`Kxx.yy`), Kapitel, Soll-Klasse,
Umsetzungsstatus, CHECK-IDs, Datenquellen und die Abbildung auf die
Checkbox-Zeilen des Referenzkatalogs (jede Referenzzeile genau einem Punkt
zugeordnet, Klasse = Vereinigung der Referenzklassen – Gate im
Release-Check). Kapitel 1–20 dieser Datei und die README-Checkliste werden
daraus generiert (`py werkzeuge/katalog_doku.py --write`); Änderungen an
Katalogpunkten nur in der Strukturdatei.

Maßgebliche Zählbasis der Checks ist `befunde.KATALOG`
(`werkzeuge/befunde.py`); die Gesamtzahl-Angaben in README, SKILL.md und
plugin.json folgen `len(befunde.KATALOG)` (Excel-Deckblatt und
stdout-Kopf zählen automatisch). Evidenz je CHECK-ID: Spalte
„Erwartungsbild" im Check-Register am Ende dieser Datei
(`testdaten/erwartung.json`, drei Referenzläufe).

## Legende

- **[R] Rule-based:** objektiv anhand definierter Regeln prüfbar
- **[P] Plausibilität:** Schwellenwert-/Vergleichsprüfung
- **[A] Anomalie:** statistischer/datengetriebener Auffälligkeitsscore
- **[X] Zusatzdaten:** Prüfung benötigt mehr als den Buchungsstapel

Umsetzung je Katalogpunkt:

- **✔ CHECK-ID** – implementiert (deterministisch, `werkzeuge/`); **✔
  Berichtsblatt/Kennzahl** – im Bericht ausgewiesen ohne eigene CHECK-ID
- **KI** – läuft über die KI-Beurteilungsschicht (Kandidaten-Export)
- **strukturell gewährleistet** – durch das DATEV-Datenformat erzwungen
- **➕ Quelle** – zusätzliche Prüfung: wird aktiv, sobald die genannte
  Datenquelle angeliefert wird (bewusst NICHT „unprüfbar"); bei
  umgesetzten Punkten benennt ein ➕-Zusatz den nicht abgedeckten Teil
- **Ausbaustufe** – mit vorhandenen Datenquellen umsetzbar, noch nicht
  implementiert (Roadmap)

## Zielarchitektur: vier Ebenen

Jeder Check trägt eine Ebene (im Bericht ausgewiesen), damit ein
„verdächtig runder Betrag" nie auf derselben Stufe steht wie eine
rechnerisch negative Kasse. Die Tabelle und das Check-Register am Ende
dieser Datei werden aus `befunde.KATALOG` generiert
(`py werkzeuge/katalog_doku.py --write`; der Build prüft die Aktualität).
Die Spalte „Klasse" der Tabellen unten und die `[R]/[P]/[A]/[X]`-Tags im
README sind dagegen die Klasse des **Soll-Katalogpunkts** (Vereinigung der
Klassen der zugeordneten Referenzkatalog-Zeilen); Ebene und Klasse des
**implementierten Checks** stehen allein im Register – beides darf
voneinander abweichen (ein Plausibilitäts-Check kann einen als [R]
klassifizierten Katalogpunkt abdecken):

<!-- KATALOG:EBENEN:START -->
| Ebene | Frage | Checks (Präfixe) |
|---|---|---|
| 1 – technische Integrität | Daten vollständig und konsistent? | DV, DQ, ST-05/06, SB-05/06, OP-05, VJ-01 |
| 2 – Regelprüfung | Verstoß gegen eindeutige Buchungs-/Bilanz-/Steuerregel? | SB-01/03/04, AF-01/03/04, US-01/03/04/06/07/08, RE-01/02, OP-01/02/04, KR, ET, PP-03/04 |
| 3 – Plausibilität | Passt der Sachverhalt zu Schwellen, Struktur, Relationen? | SB-02/07/08/09, AF-02/05, US-02/10, RE-03, OP-03/06/07, BL, VJ-02, CO, PP-01/02, GS, ST-01, FR-03, SD |
| 4 – Anomalie | Statistisch/strukturell ungewöhnlich ohne konkreten Regelverstoß? | SB-10, US-05/09, GV, ST-02/03/04/07/08, FR-01/02/04 |
<!-- KATALOG:EBENEN:END -->

---

<!-- KATALOG:SOLL:START -->
## 1. Datenvollständigkeit und technische Integrität

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K01.01 | Soll = Haben auf Beleg-, Perioden- und Jahresebene | R | strukturell gewährleistet: jede DATEV-Stapelzeile bucht Konto gegen Gegenkonto (Einzeilenformat) |
| K01.02 | Buchungen ohne Konto, Gegenkonto oder Betrag | R | ✔ DV-01 (Nullbeträge) + Import-Abweisungen des Parsers in DQ-01 |
| K01.03 | Buchungen ohne Buchungsdatum | R | ➕ GDPdU-Journal (Buchungs-/Erfassungsdatum – der Buchungsstapel führt nur das Belegdatum) |
| K01.04 | Buchungen ohne Belegdatum | R | Ausbaustufe: Zählung leerer Belegdaten in DQ-01 (der Parser warnt nur bei unlesbarem, nicht bei fehlendem Belegdatum; im DATEV-Format ist das Belegdatum Pflichtfeld) |
| K01.05 | Buchungen ohne Belegnummer oder Buchungstext | R/P | ✔ ST-05 (Quoten je Stapel) |
| K01.06 | ungültige bzw. unbekannte Konten | R | ✔ DV-03 (mit Kontenbeschriftungen) |
| K01.07 | ungültige Steuerschlüssel | R | ✔ US-03 |
| K01.08 | Buchungen außerhalb des Wirtschaftsjahres | R | ✔ ST-06 |
| K01.09 | Buchungen in nicht vorgesehenen Perioden | R | ➕ GDPdU-Journal (Buchungsperiode/Buchungsdatum) |
| K01.10 | Lücken oder Sprünge in Beleg-/Buchungsnummern | P | ✔ RE-01 (Ausgangsrechnungsnummern; Eingangsnummern bewusst ausgenommen: fremdvergeben); technische Buchungsnummern ➕ GDPdU-Journal |
| K01.11 | identische technische Buchungs-IDs | R | ➕ GDPdU-Journal mit Buchungs-IDs |
| K01.12 | inkonsistente Datensätze innerhalb desselben Buchungssatzes | R | ✔ DV-01 (Konto = Gegenkonto) |
| K01.13 | Rechtsform-Konsistenz: Mandantenname ↔ Angabe ↔ Kontenbild (KSt-/Kapital- vs. Privatkonten) | R | ✔ DQ-02 – Klassifizierung über `rechtsformen_erkennung` in `konten_config.json`; KSt-/gezeichnetes-Kapital- vs. Privatkonten-Indizien; § 1a-KStG-Vorbehalt |
| K01.14 | Eröffnungsbilanzwerte = Schlussbilanzwerte des Vorjahres, je Bilanzkonto | R | ✔ VJ-01 (mit `--susa-vorjahr`) |
| K01.15 | keine EB-Buchungen auf GuV-Konten | R | ✔ DV-02 |
| K01.16 | Saldenvorträge saldieren auf null | R | ✔ SB-06 |
| K01.17 | neue Bilanzkonten ohne nachvollziehbaren Anfangsbestand, verschwundene Vorjahreskonten mit Restbestand | P | ✔ VJ-01 (mit `--susa-vorjahr`) |

## 2. Journal- und Buchungsprüfung

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K02.01 | exakt identische Doppelbuchungen | R | ✔ ST-01 (hoch bei identischem Beleg) |
| K02.02 | wirtschaftlich wahrscheinliche Doppelbuchungen trotz unterschiedlicher Buchungs-ID | P | ✔ ST-01 (Zeitfenster `doppel_fenster_tage`) + KI |
| K02.03 | gleicher Betrag + gleicher Kreditor/Debitor + gleiches Rechnungsdatum | P | ✔ ST-01 |
| K02.04 | gleiche Rechnungsnummer mehrfach gebucht | P | ✔ RE-02 (Ausgang), KR-01 (Eingang je Kreditor) |
| K02.05 | gleicher Buchungstext/Betrag in sehr kurzem Zeitraum | P | ✔ ST-01 (gleicher Betrag auf gleicher Konto-Gegenkonto-Kombination im Zeitfenster; Buchungstext im KI-Kandidaten) |
| K02.06 | Buchung und Storno ohne erkennbaren Anlass, mehrfaches Storno und erneute Einbuchung | P | ✔ FR-01 |
| K02.07 | ungewöhnlich viele manuelle Umbuchungen | P | ➕ GDPdU-Journal (Erfassungsart/Herkunft der Buchung – der Stapel unterscheidet manuelle und automatische Buchungen nicht) |
| K02.08 | ungewöhnlich viele Abschluss-/Nachtragsbuchungen | P | ✔ GV-01 (Monatsspitzen), CO-01/CO-02 (Cut-off-Fenster); Erfassungsart ➕ GDPdU-Journal |
| K02.09 | rückdatierte Buchungen | P | ✔ RE-03 (Indiz: Rechnungsdatum entgegen Nummernfolge); vollständig ➕ GDPdU-Journal mit Erfassungsdatum |
| K02.10 | großer Abstand zwischen Beleg- und Buchungsdatum | P | ➕ GDPdU-Journal (Erfassungsdatum) |
| K02.11 | Buchungen an ungewöhnlichen Tagen oder Uhrzeiten, ungewöhnliche Buchungsaktivität einzelner Benutzer | A | ✔ ST-04 (Belegdatum Kasse: Sonn-/Feiertage); Uhrzeit/Benutzer ➕ GDPdU-Journal mit User und Zeitstempel |
| K02.12 | ungewöhnliche Konten-Gegenkonten-Kombination, erstmalig auftretende Kontierung | A | ✔ GV-03; jahresübergreifend (erstmalig gegenüber dem Vorjahr) ➕ Vorjahres-Buchungsstapel |
| K02.13 | ungewöhnliche Buchungstexte | A | KI (Kandidaten) + ET-02 (regelbasierte Textmuster) |
| K02.14 | ungewöhnliche Buchungsfrequenzen | A | ✔ GV-01 (Monatsvolumen je GuV-Konto als Näherung), SB-08 (Buchungsfrequenz der Kasse); Ausbaustufe: kontoindividuelle Frequenzerwartung (`erwartungen`-Objekt, Kap. 18) |
| K02.15 | Buchungen knapp oberhalb/unterhalb definierter Freigabegrenzen | P | ✔ FR-03 (nur mit konfigurierten `freigabegrenzen`; Default leer → begründeter Skip) |
| K02.16 | auffällige Aufteilung eines Gesamtbetrags auf mehrere Einzelbuchungen | A | ✔ ST-07 (nur Anlagen-/GWG-Zugänge knapp unter der GWG-Grenze); Ausbaustufe: allgemeines Betrags-Splitting je Konto/Geschäftspartner |

## 3. Kasse und liquide Mittel

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K03.01 | negativer Kassenbestand zu irgendeinem Zeitpunkt (§ 146 AO) | R | ✔ SB-01 (taggenauer Verlauf) |
| K03.02 | chronologisch fortgeschriebener Kassenbestand | R | ✔ Verlaufsrechnung in SB-01/SB-07 |
| K03.03 | ungewöhnlich hohe Kassenbestände | P | ✔ SB-07 |
| K03.04 | ungewöhnlich hohe Bareinzahlungen/-entnahmen, sprunghafte Kassenbestandsänderungen | P | ✔ SB-09 |
| K03.05 | ungewöhnlich viele glatte Bargeldbeträge | P | ✔ SB-10 (Kasse ↔ Privat; bei Kapitalgesellschaft begründeter Skip), ST-03 |
| K03.06 | nachträgliche Kassenbuchungen | P | ➕ GDPdU-Journal mit Erfassungsdatum |
| K03.07 | größere zeitliche Lücken in der Kassenführung | P | ✔ SB-08 |
| K03.08 | Kassenbuch gegen Finanzbuchhaltung abstimmen | X | ➕ Kassenbuch-Export |
| K03.09 | Banksaldo und Bankbewegungen gegen Kontoauszug abstimmen | X | ➕ Bankbewegungen (CAMT/CSV) |
| K03.10 | lange ungeklärte Bankbuchungen | P | ✔ SB-04 (Interims-/Verrechnungskonten zum Stichtag nicht ausgeglichen); unterjährige Klärungsdauer ➕ Bankbewegungen |
| K03.11 | ungewöhnliche Barabhebungen | P | ✔ SB-09 (kassenseitige Ausreißer), SB-10 (Kasse/Privat); bankseitig vollständig ➕ Bankbewegungen |
| K03.12 | Überweisungen auf ungewöhnliche Gegenkonten | P | ➕ Bankbewegungen mit Empfänger-IBAN/Stammdaten (GV-03 sieht nur Kombinationen mit GuV-Seite) |
| K03.13 | ungewöhnliche Geldtransfers zwischen eigenen Konten | P | ✔ SB-03 (Geldtransit gleicht sich zum Stichtag aus); Transfermuster zwischen Bankkonten ➕ Bankbewegungen |
| K03.14 | gleiche Zahlung mehrfach verbucht | R | ✔ ST-01 |
| K03.15 | gleiche Banktransaktion mehreren Rechnungen zugeordnet | X | ➕ Bankbewegungen mit Zahlungszuordnung (OPOS-Ausgleichsinformation) |

## 4. Debitoren und Forderungen

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K04.01 | Debitoren-Hauptbuch = Debitoren-Nebenbuch | R | ✔ OP-05 (OPOS-Summen je Konto, mit `--opos`) |
| K04.02 | Kreditsalden auf Debitorenkonten | P | ✔ OP-01 |
| K04.03 | ungewöhnlich hohe Forderungssalden | P | Ausbaustufe: Saldohöhe je Debitor relativ zu Umsatz und Vorjahr (Vorjahres-SuSa reicht als Datenbasis); OP-07 misst nur die Konzentration des Soll-Umsatzvolumens |
| K04.04 | lange überfällige Forderungen, OPOS-Altersstruktur 30/60/90/180/365 Tage | P | ✔ OP-03 + Berichtsblatt „OPOS-Alterung“ (mit `--opos`) |
| K04.05 | sehr alte Kleinstbeträge, sehr alte Gutschriften | P | ✔ OP-06 |
| K04.06 | ausgeglichene Rechnungen noch als offen, doppelte offene Rechnungen | R | ✔ OP-05 (Differenz OPOS-Summe ↔ Kontensaldo als Indiz); ➕ OPOS mit Ausgleichsinformation (Zahlungs-/Ausgleichshistorie) |
| K04.07 | Zahlung ohne korrespondierende Forderung | P | ✔ OP-01 (Habensaldo) |
| K04.08 | Rechnung ohne Zahlung trotz ungewöhnlich langen Zeitraums | P | ✔ OP-03 (überfällige offene Posten) |
| K04.09 | ungewöhnlich viele Teilzahlungen | P | ➕ OPOS mit Ausgleichsinformation (Teilzahlungshistorie) |
| K04.10 | ungewöhnliche Verrechnung zwischen Kunden | P | ✔ OP-04 (Direktverrechnung zwischen Personenkonten) |
| K04.11 | Forderungen deutlich außerhalb des normalen Zahlungsverhaltens eines Kunden | A | ➕ Zahlungshistorie je Kunde (OPOS-Historie/Vorjahr) |
| K04.12 | Konzentrationsrisiko einzelner Debitoren | A | ✔ OP-07 |
| K04.13 | Forderungsanstieg ohne entsprechende Umsatzentwicklung | P | ➕ Vorjahresdaten (Forderungs- und Umsatzentwicklung im Vergleich; Ausbaustufe auf Basis der Vorjahres-SuSa) |
| K04.14 | Zahlungseingänge nach Bilanzstichtag, Mahnstatus, Wertberichtigungen gegen Altersstruktur, Forderungen gegen verbundene Unternehmen | X | ➕ Folgeperiode (Zahlungseingänge), Mahnwesen, Kontenzuordnung verbundener Unternehmen |

## 5. Kreditoren und Verbindlichkeiten

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K05.01 | Kreditoren-Hauptbuch = Kreditoren-Nebenbuch | R | ✔ OP-05 (mit `--opos`) |
| K05.02 | Sollsalden auf Kreditorenkonten | P | ✔ OP-02 |
| K05.03 | ungewöhnlich hohe Verbindlichkeiten | P | ➕ Vorjahresdaten (Relation zu Material-/Gesamtaufwand; Ausbaustufe auf Basis der Vorjahres-SuSa) |
| K05.04 | sehr alte offene Verbindlichkeiten, alte Kreditorengutschriften | P | ✔ OP-03, OP-06 |
| K05.05 | identische Eingangsrechnung mehrfach erfasst | R | ✔ ST-01 |
| K05.06 | gleiche Rechnungsnummer bei gleichem Kreditor | P | ✔ KR-01 |
| K05.07 | gleicher Betrag/Rechnungsdatum/Kreditor mit abweichender Rechnungsnummer | P | ✔ ST-01 (mittel: gleicher Betrag und Partner im Zeitfenster ohne identischen Beleg) |
| K05.08 | doppelte Zahlungen | R/X | ✔ ST-01; Abgleich gegen Bank ➕ Bankbewegungen |
| K05.09 | Zahlung ohne offene Verbindlichkeit | P | ✔ OP-02 (Sollsaldo) |
| K05.10 | ungewöhnliche Vorauszahlungen | P | ✔ OP-02 (Sollsaldo auf Kreditor als Indiz); Vorauszahlungs-Kennzeichnung ➕ OPOS-Detail |
| K05.11 | ungewöhnlich viele manuelle Kreditorenbuchungen | P | ➕ GDPdU-Journal (Erfassungsart) |
| K05.12 | ungewöhnliches Kreditorenkonto für bestimmte Kostenarten | A | ✔ GV-03 |
| K05.13 | erhebliche Änderung des Zahlungsprofils eines Lieferanten | A | ➕ Vorjahres-Buchungsstapel/Bankbewegungen (Zahlungsprofil im Zeitvergleich) |
| K05.14 | Verbindlichkeiten gegen Zahlungen nach Bilanzstichtag, Verbindlichkeiten gegenüber verbundenen Unternehmen | X | ➕ Folgeperiode (Zahlungen nach Stichtag), Kontenzuordnung verbundener Unternehmen |

## 6. Anlagevermögen und AfA

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K06.01 | Sachkonten Anlagevermögen, kumulierte AfA, Anlagenzugänge und -abgänge = Anlagenbuchhaltung | R/X | ➕ Anlagenspiegel-Export |
| K06.02 | Wirtschaftsgut vorhanden, aber keine AfA | R | ✔ AF-01 (nur Anlagenzugänge bei völlig fehlender AfA-Buchung); je Wirtschaftsgut ➕ Anlagenspiegel |
| K06.03 | AfA auf vollständig abgegangenes Wirtschaftsgut | R | ✔ AF-02 (Kontenebene: AfA ohne Anlagevermögen); je Wirtschaftsgut ➕ Anlagenspiegel |
| K06.04 | AfA auf nicht abnutzbares Anlagevermögen (Grund und Boden) | R | ✔ AF-03 |
| K06.05 | negativer Buchwert | R | ✔ SB-02 (Saldenvorzeichen der Anlagenkonten) |
| K06.06 | je Wirtschaftsgut: AfA über dem abschreibbaren Restwert, Restbuchwert nach Ablauf der Nutzungsdauer, AfA vor Anschaffung oder nach Abgang, zeitanteilige AfA, Nutzungsdauer und AfA-Methode gegen Stammdaten | R/P | ➕ Anlagenspiegel (Einzelprüfungen je Wirtschaftsgut) |
| K06.07 | außergewöhnlich hohe/geringe AfA, erhebliche Änderung der AfA gegenüber Vorjahr | P | ✔ VJ-02 (AfA-Konten gegen Vorjahr, mit `--susa-vorjahr`); AfA-Satz je Wirtschaftsgut ➕ Anlagenspiegel |
| K06.08 | Anlagenzugang ohne korrespondierende Kreditoren-/Bankbuchung | P | Ausbaustufe: Gegenkonten-Erwartung je Anlagenkonto (`erwartungen`-Objekt, Kap. 18); GV-03 sieht nur Kombinationen mit GuV-Seite |
| K06.09 | Investitionskonto mit ungewöhnlich vielen Kleinstbeträgen | P | ✔ AF-04 (Zugänge im GWG-Wahlrechtsband), ST-07 (Cluster knapp unter der GWG-Grenze); Ausbaustufe: Häufung von Kleinstbeträgen je Investitionskonto |
| K06.10 | größere Anschaffungen unmittelbar als Aufwand gebucht, aktivierungspflichtige Anschaffungen auf Reparatur-/Instandhaltungskonten | P | ✔ AF-05 + KI (Kandidaten = Befunde mit KI-Kennzeichen, u. a. AF-05/ST-02/ET-02, sowie Buchungen der Kontengruppe `sachfremd_llm` ab `llm_kandidat_min_eur`) |
| K06.11 | mögliche laufende Aufwendungen unplausibel aktiviert | P | KI, soweit ein Anlagenzugang über ST-02/ST-07 in die Kandidatenlage gelangt |
| K06.12 | GWG-/Sammelpostenbehandlung nach hinterlegten steuerlichen Parametern | R/P | ✔ AF-04 (Grenzen), ST-07 (Schwellen-Splitting) |
| K06.13 | außerplanmäßige Abschreibungen auf dokumentierte Wertminderungen, Anlagenabgang gegen Verkaufserlös und Abgangsergebnis | X | ➕ Anlagenspiegel/Belege |

## 7. Vorräte und Waren

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K07.01 | Vorratskonten gegen Inventurlisten | R/X | ➕ Inventurlisten |
| K07.02 | ungewöhnlich starke Bestandsänderung | P | ➕ Vorjahresdaten/Inventur (Bestandsveränderung im Zeitvergleich; Ausbaustufe auf Basis der Vorjahres-SuSa) |
| K07.03 | negativer Warenbestand, soweit Mengendaten vorhanden | P | ➕ Warenwirtschaftsdaten (Mengen); Ausbaustufe: wertmäßiges Saldenvorzeichen der Bestandskonten (Kontengruppe `vorraete` in SB-02) |
| K07.04 | Lagerbestand ohne Bewegungen über längere Zeit, langsam drehende Artikel, hohe Reichweiten | P/A | ➕ Warenwirtschaftsdaten (Mengen, Bewegungen, Reichweiten) |
| K07.05 | Warenaufwand ohne korrespondierende Umsatzentwicklung, Umsatzentwicklung ohne korrespondierende Warenbewegung | P | ✔ Kennzahlen-Ausweis (Materialquote, Rohertrag; Erlöse Vorjahr mit `--susa-vorjahr`) |
| K07.06 | auffällige Buchungen auf Bestandskonten unmittelbar vor Stichtag | P | Ausbaustufe: Cut-off-Fenster für Bestandskonten (Kontengruppe `vorraete`); CO-01/CO-02 prüfen nur Erlös-/Aufwandskonten |
| K07.07 | Inventurdifferenzen, Niederstwert-/Wertberichtigungsindikatoren | X | ➕ Inventur-/Warenwirtschaftsdaten |

## 8. Sonstige Bilanzkonten

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K08.01 | regelmäßig wiederkehrende Zahlungen (Versicherungen, Mieten, Wartungen) über den Stichtag hinweg ohne RAP | P | ✔ BL-01 (getrennt je Richtung ARAP/PRAP, § 250 Abs. 1/2 HGB) |
| K08.02 | RAP aus Vorjahr nicht aufgelöst | R | ✔ BL-01 (ARAP bzw. PRAP ohne Auflösung); Saldenvorzeichen ARAP/PRAP SB-02 |
| K08.03 | ungewöhnlich alte RAP-Positionen, erhebliche RAP-Veränderungen ohne Geschäftsentwicklung | P | ➕ Vorjahresdaten |
| K08.04 | bestehende Vorjahresrückstellung ohne Bewegung | P | ✔ BL-02 |
| K08.05 | jährlich identische Rückstellungsbeträge | P | ✔ BL-02 (mit `--susa-vorjahr`) |
| K08.06 | Rückstellungsauflösung ohne entsprechenden Sachverhalt, Aufwand mit Rückstellungscharakter direkt als Verbindlichkeit oder Aufwand behandelt | P | ➕ Unterlagen zum Rückstellungsgrund (Verträge, Leistungszeiträume, Abrechnungen) |
| K08.07 | starke Schwankung einzelner Rückstellungen, Abzinsung langfristiger Rückstellungen | P/X | ➕ Vorjahresdaten/Verträge |
| K08.08 | latente Steuern: Bestand/Ansatz und Steuersatz-Staffel (KSt-Senkung ab 2028; § 274, § 274a HGB) | P | ✔ BL-05 (Kontenbereiche `latente_steuern` konfigurieren); Bewertung der Differenzen ➕ Steuerbilanz/Überleitungsrechnung |
| K08.09 | Darlehenssaldo gegen Tilgungsplan, Zinsaufwand gegen Zinssatz und Saldo, Laufzeiten und Fristigkeiten | R/X | ➕ Darlehensverträge/Tilgungspläne |
| K08.10 | Tilgung auf Zinskonto bzw. Zins auf Darlehenskonto | P | ✔ BL-03 (Indiz nur bei völlig fehlendem Zinsaufwand); Zins-/Tilgungsverprobung ➕ Darlehensverträge |
| K08.11 | Darlehen ohne Zinsbuchungen | P | ✔ BL-03 |
| K08.12 | ungewöhnliche Gesellschafterdarlehen | P | ✔ GS-01 (Bewegungen auf Gesellschafterkonten); Fremdüblichkeit von Zins und Laufzeit ➕ Darlehensverträge |
| K08.13 | Vortrag des Vorjahres, Ergebnisverwendung rechnerisch prüfen | R/X | ✔ VJ-01 (EB der Eigenkapitalkonten gegen Vorjahres-SuSa); Ergebnisverwendung ➕ Gewinnverwendungsbeschluss/Jahresabschluss Vorjahr |
| K08.14 | Buchungen unmittelbar auf Eigenkapitalkonten, unterjährige Buchungen auf Gewinnvortrag | P | ✔ BL-04 |
| K08.15 | Interims-/Verrechnungskonten und durchlaufende Posten zum Stichtag ausgeglichen | R | ✔ SB-04 |
| K08.16 | ungewöhnliche Einlagen/Entnahmen, Gesellschafterkonten mit ungewöhnlichen Salden | P | ✔ PP-02, SB-10, GS-01 |
| K08.17 | Privatkonten bei Kapitalgesellschaft bebucht | R | ✔ PP-04 (mit `--rechtsform`; PP-01/02 und SB-10 werden bei Kapitalgesellschaft begründet übersprungen) |
| K08.18 | Kapitalkontenentwicklung je Gesellschafter (PersG: Kapitalkonten I/II, Verlust-/Darlehenskonten), verrechenbare Verluste § 15a EStG | R/X | ➕ Kapitalkontenentwicklung, Gesellschaftsvertrag |

## 9. GuV- und Kontenplausibilitäten

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K09.01 | jedes GuV-Konto gegen Vorjahr: starke absolute/relative Veränderung, Vorzeichenwechsel, erstmalig mit wesentlichem Saldo, plötzlich ohne Saldo | P | ✔ VJ-02 (mit `--susa-vorjahr`) |
| K09.02 | jedes GuV-Konto gegen Vorperiode | P | ✔ GV-01 (Monatsverlauf innerhalb des Jahres); Vorperioden/Monatsreihen des Vorjahres ➕ Vorjahres-Buchungsstapel |
| K09.03 | Monatsverlauf jedes wesentlichen Kontos, ungewöhnliche Monatsspitzen | P/A | ✔ GV-01 |
| K09.04 | ungewöhnliche saisonale Abweichungen | A | ➕ Vorjahres-Buchungsstapel (Saisonmuster im Mehrjahresvergleich) |
| K09.05 | Verhältniskennzahlen: Materialaufwand/Umsatz, Personalaufwand/Umsatz, Raumkosten/Umsatz, Werbekosten/Umsatz, Rohertrag/Rohmarge | P | ✔ Kennzahlen-Ausweis (Material-, Personal-, Mietkosten-, Werbekostenquote, Rohertrag) |
| K09.06 | Fahrzeugkosten/Umsatz | P | Ausbaustufe: Quote bewusst nicht ausgewiesen (unüblich); Fahrzeugkosten-Ausreißer über ST-02, private Kfz-Nutzung über PP-01 (nur Personengesellschaft) |
| K09.07 | weitere Verhältniskennzahlen: Fremdleistungen/Umsatz, Abschreibungen/Anlagevermögen, Zinsaufwand/Finanzverbindlichkeiten, Forderungen/Umsatz, Verbindlichkeiten/Materialaufwand, Umsatz pro Mitarbeiter | P | Ausbaustufe: weitere Kontengruppen in `konten_config.json` und Kennzahlen-Ausweis; Benchmarking ➕ Vorjahr/Branchenwerte; Umsatz pro Mitarbeiter ➕ Mitarbeiterzahl (Personaldaten) |
| K09.08 | ungewöhnliche Gegenkonten | A | ✔ GV-03 |
| K09.09 | sachfremde Buchungstexte | A | KI (Kandidaten) |
| K09.10 | ungewöhnliche Geschäftspartner | A | ✔ GV-03 (Personenkonto als seltenes Gegenkonto), FR-02 (Einmal-Kreditoren) |
| K09.11 | außergewöhnlich hohe Einzelbuchungen | P | ✔ ST-02 |
| K09.12 | ungewöhnlich viele Kleinstbuchungen | P | Ausbaustufe: Kleinstbuchungs-Häufung je Konto (Betragsbandbreite als Erwartung je Konto, Kap. 18) |
| K09.13 | ungewöhnlich viele glatte Beträge | P | ✔ ST-03, FR-04 |
| K09.14 | außergewöhnliche Beträge kurz vor Periodenende | P | ✔ CO-01 (Erlösseite); betragsgroße Einzelfälle zudem ST-02 |
| K09.15 | außerordentlich hohe Gutschriften, starke Gegenbuchungen auf normalerweise einseitigen Konten | P | ✔ GV-02 |

## 10. Umsatzsteuer

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K10.01 | Erlöskonto ↔ Steuerschlüssel und Aufwandskonto ↔ Vorsteuerschlüssel plausibel | R | ✔ US-05 (Schlüsselprofil je Sachkonto), US-08 (Automatikkonto-Konflikt) |
| K10.02 | steuerpflichtiges Erlöskonto ohne Umsatzsteuer, steuerfreies Erlöskonto mit Umsatzsteuer | R | ✔ US-08 (Automatikkonto), US-05 (Schlüsselprofil), US-06 (Verprobung mit SuSa) |
| K10.03 | Vorsteuerkonto ohne korrespondierende Bemessungsgrundlage | R | ✔ US-02 (Direktbuchungen auf Steuerkonten) |
| K10.04 | Steuerbetrag gegen Bemessungsgrundlage, Steuersatz gegen verwendeten Steuerschlüssel | R | ✔ US-06/US-07 (rechnerische USt/VSt aus Erlösen/Aufwand und Schlüsseln gegen Steuerkonten, mit SuSa), US-03 (Schlüsselkatalog mit Sätzen; Gültigkeit nur für die 16-%-Sätze 07–12/2020) |
| K10.05 | ungewöhnlicher Steuerschlüssel für bestimmtes Sachkonto | P | ✔ US-05 |
| K10.06 | Steuerschlüssel gegenüber üblicher Behandlung desselben Lieferanten/Kunden verändert | P | ✔ US-09 |
| K10.07 | Buchung mit falschem Vorzeichen auf Umsatz-/Vorsteuerkonten | R/P | ✔ US-02 (Direktbuchungen auf Steuerkonten als Indiz); Ausbaustufe: Vorzeichen-/Richtungsprüfung je Steuerkonto (Steuerkontengruppen in SB-02) |
| K10.08 | Umsatzsteuerkonten gegen Umsatzsteuer-Voranmeldung, Jahreswerte gegen Umsatzsteuer-Jahreserklärung | R | ➕ UStVA-/Erklärungswerte |
| K10.09 | Vorsteuer auf Konten mit typischerweise eingeschränktem Abzug | R/P | ✔ US-01 |
| K10.10 | ungewöhnlich hoher Vorsteuerbetrag | P | ✔ ST-02 (mittelbar über den Bruttobetrag der Aufwands-/Anlagenbuchung; Vorsteuerkonten selbst sind Bilanzkonten) |
| K10.11 | Vorsteuer ohne Kreditor bzw. Belegbezug | P | ✔ US-10 |
| K10.12 | Rechnung vorhanden, Pflichtangaben §§ 14, 14a UStG, Leistungsempfänger und Leistungsbezug, Leistungs-/Rechnungsdatum, zeitlich zutreffender Vorsteuerabzug | X | ➕ digitale Belege |
| K10.13 | Reverse Charge § 13b UStG: ausländischer Kreditor ohne 13b-Schlüssel, 13b-Schlüssel bei untypischem Sachverhalt, Abstimmung USt/VSt und Bemessungsgrundlage, 13b-Sachverhalte ohne Steuerbuchung | R/P | ➕ 13b-Schlüsselkatalog + Kreditorenstammdaten (Sitzland); Stapelfelder vorhanden (Ausbaustufe) |
| K10.14 | EU-Sachverhalte: innergemeinschaftlicher Erwerb/Lieferung, Reverse Charge bei EU-Dienstleistungen, Leistungsortprüfung, USt-IdNr., Zusammenfassende Meldung, Intrastat | P/X | ➕ EU-Schlüsselkatalog + Stammdaten (USt-IdNr., Land), ZM-/Intrastat-Daten |
| K10.15 | Berichtigungen § 17 UStG (Gutschrift, Skonto, Boni ohne Steuerkorrektur; Uneinbringlichkeit und nachträgliche Zahlung), § 15a UStG | P/X | ➕ Skonto-Feld-Auswertung, OPOS-Historie, Belege (§ 15a: Nutzungsnachweise) |
| K10.16 | unrichtiger oder unberechtigter Steuerausweis § 14c UStG (Steuersatz, steuerfreie Sachverhalte, nicht berechtigte Aussteller) | X | ➕ digitale Belege |

## 11. Ertragsteuerliche Auffälligkeiten

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K11.01 | Geschenke über der Abzugsgrenze (§ 4 Abs. 5 Satz 1 Nr. 1 EStG) | R | ✔ ET-01 – Grenze 35/50 EUR nach WJ-Beginn; Maßstab netto, ohne VSt-Abzug brutto (`vst_abzugsberechtigt`) |
| K11.02 | Geschenke auf falschem Konto | P | ✔ ET-02 (Textmuster „Geschenk“) |
| K11.03 | Geschenke-Summe je Empfänger und Jahr gegen die Freigrenze | R | ➕ Empfängeraufzeichnung (§ 4 Abs. 7 EStG) |
| K11.04 | Bewirtungsaufwendungen mit unplausibler steuerlicher Behandlung | P | ✔ US-04 (fehlender nicht abziehbarer 30-%-Anteil = mittel; Quote unter `bewirtung_nabz_quote_min` = Hinweis) |
| K11.05 | Geldbußen/Ordnungsgelder als abzugsfähiger Aufwand behandelt | P | ✔ ET-02 (Textmuster) |
| K11.06 | Gewerbesteuer als abzugsfähige Betriebsausgabe behandelt | P | ✔ ET-02 (Textmuster) |
| K11.07 | Spenden/Sponsoring auf gewöhnlichen Werbekonten | P | ✔ ET-02 (Textmuster „Spende“/„Sponsoring“) |
| K11.08 | private bzw. gesellschaftlich veranlasste Aufwendungen auf Betriebsausgabenkonten | P | KI (Kandidaten) + GS-01; Kfz-Kosten ohne erkennbaren Privatanteil PP-01 (nur Personengesellschaft) |
| K11.09 | außergewöhnlich hohe Reise-, Fahrzeug- und Repräsentationskosten | P | ✔ ST-02 (Betragsausreißer) + KI (Reise- und Repräsentationskosten liegen in der Kandidaten-Kontengruppe `sachfremd_llm`; Fahrzeugkosten nur über ST-02) |
| K11.10 | Gesellschafteraufwendungen auf allgemeinen Sachkonten | P | ✔ GS-01 + KI |
| K11.11 | mögliche verdeckte Gewinnausschüttungs-Sachverhalte (nur Review-Hinweis) | P | KI (Urteil mit Begründung) |
| K11.12 | nicht abziehbare Betriebsausgaben nicht getrennt erfasst (§ 4 Abs. 7 EStG) | P | ✔ ET-01/ET-02 (Buchung auf allgemeinem Konto als Indiz; Hinweis auf § 4 Abs. 7 EStG in den Empfehlungstexten) |
| K11.13 | ungewöhnliche Privatkontenbewegungen | P | ✔ PP-02, SB-10 |

## 12. Lohn- und Personalverrechnung

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K12.01 | Lohnsteuer- und Sozialversicherungsverbindlichkeiten gegen Lohnabrechnung | R/X | ✔ PP-03 (Minimum: Lohnaufwand ohne LSt-/SV-Verbindlichkeiten); Abstimmung gegen die Abrechnung ➕ Lohnjournal |
| K12.02 | Lohnjournal gegen Finanzbuchhaltung, Nettolohnverbindlichkeiten gegen Zahlungen | R/X | ➕ Lohnjournal/Bankbewegungen |
| K12.03 | ungewöhnliche manuelle Personalbuchungen | P | ✔ GV-03 (seltene Gegenkonten auf Lohnkonten); Erfassungsart ➕ GDPdU-Journal |
| K12.04 | erhebliche Veränderung der Personalkosten | P | ✔ VJ-02 (mit `--susa-vorjahr`) + Kennzahl Personalquote |
| K12.05 | Personalkosten ohne entsprechende Mitarbeiterentwicklung | P | ➕ Personaldaten (Mitarbeiterzahl im Zeitverlauf) |
| K12.06 | Einmalzahlungen/Ausreißer | P | ✔ ST-02 (Betragsausreißer je Konto), GV-01 (Monatsspitzen) |
| K12.07 | negative Lohn-/Gehaltsaufwendungen | P | ✔ GV-02 |
| K12.08 | Mitarbeiterzahlungen außerhalb der üblichen Lohnkonten | P | ✔ GV-03 (z. B. Barlohn) |
| K12.09 | Zahlungen an ehemalige Mitarbeiter | P | ➕ Personaldaten (Austrittsdaten) + Stammdaten/Bankverbindungen |
| K12.10 | Rückstellungen für Urlaub/Boni | X | ➕ Personaldaten (Urlaubs-/Bonusansprüche) |

## 13. Periodenabgrenzung und Cut-off

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K13.01 | Rechnungsdatum und Buchungsdatum über die Jahresgrenze hinweg (Dezember/Januar) | P | ✔ CO-02 (Aufwand im Nachlauf-Fenster des Folgejahres-Stapels), CO-01 (Erlöse vor WJ-Ende); Rechnungs- gegen Buchungsdatum ➕ Folgeperioden-Journal mit Erfassungsdatum |
| K13.02 | große Erlösbuchungen in den letzten Tagen des Jahres | P | ✔ CO-01 (Fenster `cutoff_fenster_vor_tage` = 14 Tage strikt vor dem WJ-Ende aus dem DATEV-Header; WJ ≠ Kalenderjahr möglich, nie 31.12. hartkodiert) |
| K13.03 | große Erlösstornos und ungewöhnliche Gutschriften unmittelbar nach Jahresende | P | Ausbaustufe: erlösseitiger Nachlauf (Stornos/Gutschriften) im Folgejahres-Stapel (`--stapel-folgejahr`) |
| K13.04 | große Aufwandsbuchungen unmittelbar nach Jahresende, verspätete Eingangsrechnungen mit Vorjahresbezug | P | ✔ CO-02 (Fenster `cutoff_fenster_nach_tage` = 14 Tage; Datenquelle optionaler Folgejahres-Stapel `--stapel-folgejahr`, ohne Lieferung begründeter Skip) |
| K13.05 | Leistungsdatum gegen Buchungsperiode, Wareneingang gegen Eingangsrechnung, Ausgangsrechnung gegen Liefer-/Leistungsdatum | X | ➕ Belege/Warenwirtschaft; die KI-Beurteilung der CO-01/CO-02-Kandidaten nutzt den Buchungstext als Leistungsdatum-Indiz |
| K13.06 | wiederkehrende Jahreskosten/-erlöse ohne Abgrenzung | P | ✔ BL-01 |
| K13.07 | ungewöhnlich viele Abschlussbuchungen nach Periodenschluss | P | ➕ GDPdU-Journal (Erfassungsdatum) |

## 14. Intercompany und Gesellschafter

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K14.01 | Spiegelbild-Abstimmungen (Forderung A = Verbindlichkeit B, IC-Umsatz = IC-Aufwand, Darlehenssalden, Zinsaufwand/Zinsertrag), ungeklärte Intercompany-Differenzen | R/P/X | ➕ Daten der Gegenseite |
| K14.02 | Bewegungen auf Gesellschafterkonten ohne eindeutigen Gegenposten, ungewöhnliche Zahlungen/Forderungen/Verbindlichkeiten gegenüber Gesellschaftern, privat wirkende Aufwendungen mit Gesellschafterbezug | P | ✔ GS-01 + KI |
| K14.03 | Sonder-/Ergänzungsbilanzen und Sondervergütungen (§ 15 Abs. 1 Satz 1 Nr. 2 EStG) bei Mitunternehmerschaften | X | ➕ Sonder-/Ergänzungsbilanzen, Gewinnfeststellung |

## 15. Stammdatenprüfung

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K15.01 | identische Lieferanten/Kunden mehrfach angelegt | R | ✔ SD-01 (Bezeichnungen der Personenkonten) |
| K15.02 | nahezu identische Namen/Adressen | P | ✔ SD-01 (Gleichheit nach Trim/Kleinschreibung); Ausbaustufe: unscharfer Namensabgleich auf den Kontenbeschriftungen; Adressen ➕ Stammdaten-Export |
| K15.03 | IBAN-Dubletten, Adress-/Bankverbindungsabgleich Lieferant/Mitarbeiter/Kunde, Bankverbindungs-Änderung vor hoher Zahlung, häufig geänderte Stammdaten, fehlende Pflichtfelder | R/P | ➕ Debitoren-/Kreditorenstammdaten (IBAN, Adresse, Änderungshistorie, Pflichtfelder) |
| K15.04 | neue Kreditoren mit unmittelbar hohem Zahlungsvolumen | P | ✔ FR-02 (Kreditoren mit wenigen Buchungen und hohem Volumen); Neuanlage-Zeitpunkt ➕ Vorjahres-Buchungsstapel/Stammdaten |
| K15.05 | lange inaktive Kreditoren plötzlich wieder verwendet | P | ➕ Vorjahres-Buchungsstapel (Aktivitätshistorie je Kreditor) |

## 16. Fraud-/Forensic-Indikatoren

Nur Risikosignale, keine Fehlernachweise; Ebene und Klasse je Check laut Check-Register.

| ID | Katalogpunkt | Klasse | Umsetzung |
|---|---|---|---|
| K16.01 | auffällig runde Beträge, Häufung bestimmter Endziffern | A | ✔ ST-03, FR-04 |
| K16.02 | Benford-Analyse als ergänzendes Screening | A | ✔ ST-08 – ab `benford_min_n` GuV-Buchungen (Default 300; konservative eigene Kalibrierung, siehe README „Methodik“) |
| K16.03 | wiederkehrende Beträge knapp unterhalb von Freigabegrenzen, Aufteilung größerer Beträge | A | ✔ FR-03 (nur mit konfigurierten `freigabegrenzen`), ST-07 (nur Anlagen-/GWG-Zugänge knapp unter der GWG-Grenze) |
| K16.04 | ungewöhnliche Kombination Mitarbeiter/Lieferant | A | ➕ Stammdaten (Mitarbeiter-/Lieferantenabgleich: Adresse, Bankverbindung) |
| K16.05 | ungewöhnliche Kombination Benutzer/Konto, Buchungen außerhalb typischer Geschäftszeiten, außergewöhnlich viele Buchungen eines einzelnen Users | A | ➕ GDPdU-Journal mit User und Zeitstempel |
| K16.06 | Buchungen an Wochenenden/Feiertagen | A | ✔ ST-04 (Kasse, Belegdatum) – bundeseinheitliche Feiertage, Landesfeiertage über `feiertage_zusatz` |
| K16.07 | ungewöhnlich hohe manuelle Buchungsquote | A | ➕ GDPdU-Journal (Erfassungsart) |
| K16.08 | außergewöhnlich hohe Stornoquote | A | ✔ FR-01 |
| K16.09 | neue Lieferanten kurz vor großen Zahlungen, Lieferanten mit nur einer einzigen großen Transaktion | A | ✔ FR-02 (Lieferanten mit nur einer oder wenigen großen Transaktionen); Zeitpunkt der Neuanlage vor großen Zahlungen ➕ Vorjahres-Buchungsstapel/Stammdaten |
| K16.10 | ungewöhnliche Freitexte und Kontierungswege | A | ✔ GV-03 + KI |
| K16.11 | Zahlung an unbekannte IBAN, Änderung der Lieferanten-IBAN kurz vor Zahlung, gleiche IBAN bei unabhängigen Geschäftspartnern | A | ➕ Stammdaten/Bankbewegungen (IBAN-Muster) |
| K16.12 | außergewöhnliche Buchungen unmittelbar vor Abschluss | A | ✔ CO-01 (erlösseitig), CO-02 (aufwandsseitig nach WJ-Ende, fakultativ mit `--stapel-folgejahr`) |
| K16.13 | Storno unmittelbar nach Stichtag | A | Ausbaustufe: Storno-Auswertung im Folgejahres-Stapel (`--stapel-folgejahr`) |

## 17. Gesamtabschluss und Cross-Checks

| ID | Querverprobung | Klasse | Umsetzung |
|---|---|---|---|
| K17.01 | Stapel ↔ Summen- und Saldenliste | – | ✔ SB-05 |
| K17.02 | Stapel ↔ Bilanz/GuV, Ergebnis Finanzbuchhaltung ↔ Jahresabschluss, Kontenzuordnung ↔ Bilanz-/GuV-Position | – | ✔ vereinfachte Bilanz- und GuV-Blätter mit Vorjahresspalte, formelverknüpft mit „Salden je Konto“ (Positions-Spalte, Kontrolle Aktiva = Passiva); amtliche Gliederungstiefe § 266/§ 275 HGB ➕ Positions-Zuordnungstabelle je Konto |
| K17.03 | Schlussbilanz Vorjahr ↔ Eröffnungsbilanz | – | ✔ VJ-01 |
| K17.04 | Vorjahreswerte ↔ aktuelle Vergleichswerte | – | ✔ VJ-02 (GuV je Konto), Vorjahresspalte der Bilanz-/GuV-Blätter |
| K17.05 | Sachkonten ↔ Debitoren-/Kreditoren-Nebenbuch (OPOS) | – | ✔ OP-05 |
| K17.06 | OPOS ↔ Altersstruktur | – | ✔ Blatt „OPOS-Alterung“ |
| K17.07 | Umsatzsteuerkonten ↔ rechnerische USt/VSt | – | ✔ US-06/US-07 |
| K17.08 | Umsatzsteuerkonten ↔ UStVA und USt-Jahreserklärung | – | ➕ UStVA-/Erklärungswerte |
| K17.09 | Anhangangaben und größenabhängige Erleichterungen (§§ 284–288, § 274a, § 276 HGB) | – | ➕ Anhang-Checkliste je Größenklasse; Größenklassen-Indikation (§ 267, § 267a HGB) läuft bereits als Kennzahl (ohne Ø-Arbeitnehmerzahl) |
| K17.10 | Sachkonten ↔ Anlagen-/Lohnbuchhaltung, Bank, Kasse; EU-Umsätze ↔ ZM; Warenbestand ↔ Inventur; Darlehen ↔ Verträge; Forderungen/Verbindlichkeiten ↔ Zahlungen nach Stichtag; Intercompany A ↔ B | – | ➕ jeweilige Datenquelle (siehe 20.) |

## 18. Kontenspezifische Erwartungslogik

Teilweise umgesetzt über Kontengruppen-Erwartungen in
`werkzeuge/konten_config.json`: erwartetes Vorzeichen (`SB-02`), übliche
Steuerschlüssel dynamisch (`US-05`/`US-08`/`US-09`), Betragsbandbreite
dynamisch (`ST-02`), Buchungsfrequenz (`SB-08`), erlaubte Themen je Konto
(`ET-02`). Ausbaustufe: `erwartungen`-Objekt je Einzelkonto
(Gegenkonten-Whitelist, Monatsverteilung, Vorjahresabweichung) – Struktur
siehe Referenzkatalog Kap. 18.

## 19. Ergebnisstruktur je Treffer

Jeder Befund führt: `check_id`, Prüfbereich, **Ebene (1–4)**, **Klasse
(R/P/A/X)**, Schwere, Konto, Gegenkonto, Datum, Betrag, Beleg,
Buchungstext, Befundtext (erwarteter/tatsächlicher Zustand), empfohlene
Prüfhandlung, Quelle (Datei:Zeile), KI-Kennzeichen sowie leere
**Review-Spalten** (Status, Bearbeiter, Kommentar) im Excel. Die
KI-Schicht ergänzt je Kandidat Urteil, Begründung, Schwere und
**Konfidenz**. Offen (Ausbaustufe): Regelversion je Check,
Wesentlichkeitsbezug zur Bilanzsumme.

## 20. Datenquellen

| # | Quelle | Status | Katalogpunkte |
|---|---|---|---|
| 1 | Buchungsstapel (EXTF/DTVF Kat. 21) | ✔ Pflichtquelle | alle (Pflichtquelle) |
| 2 | Summen- und Saldenliste | ✔ optional (`--susa`) → SB-05, US-06/07 | K10.02, K10.04, K17.01, K17.07 |
| 3 | Kontenplan des Mandanten (= Kontenbeschriftungen, Kat. 20) | ✔ optional, automatisch erkannt bzw. `--kontenplan` → DV-03, SD-01, Nutzungsgrad-Kennzahl | K01.06, K15.01 |
| 4/5 | Debitoren-/Kreditorenstammdaten | ➕ IBAN-/Adress-/Dubletten-Prüfungen, 13b-/EU-Sachverhalte | K15.02, K15.04, K16.09 · ➕ K03.12, K10.13, K10.14, K12.09, K15.03, K16.04, K16.11 |
| 6/7 | OPOS Debitoren/Kreditoren | ✔ optional (`--opos`) → OP-03/05/06, Alterung; Ausgleichs-/Zahlungshistorie ➕ | K04.01, K04.04, K04.05, K04.06, K04.08, K05.01, K05.04, K05.10, K17.05, K17.06 · ➕ K03.15, K04.09, K04.11, K04.14, K10.15 |
| 8 | Anlagenbuchhaltung (Anlagenspiegel) | ➕ AfA-Einzelprüfungen je Wirtschaftsgut | K06.02, K06.03, K06.07 · ➕ K06.01, K06.06, K06.13, K17.10 |
| 9 | Bankbewegungen (CAMT/CSV) | ➕ Bank-/Zahlungsabgleich | K03.10, K03.11, K03.13, K05.08 · ➕ K03.09, K03.12, K03.15, K05.13, K12.02, K16.11, K17.10 |
| 10 | Kassenbuch | ➕ Kassenbuch-Abstimmung | ➕ K03.08, K17.10 |
| 11 | digitale Belege | ➕ §§ 14/15-Rechnungsprüfung, § 14c UStG, Leistungsdatum | ➕ K06.13, K10.12, K10.15, K10.16, K13.05 |
| 12 | Steuerschlüssel-Katalog | ✔ `konten_config.json` (erweiterbar); 13b-/EU-Schlüssel ➕ | ➕ K10.13, K10.14 |
| 13 | Kostenstellen/Kostenträger | optional (nicht unverzichtbar) – Feld wird gelesen; KOST-Auswertung Ausbaustufe | – |
| 14 | Benutzer-/Erfassungsinfos (GDPdU-Journal) | ➕ User-/Zeit-/Rückdatierungs-Checks, Erfassungsart, Buchungs-IDs | K01.10, K02.08, K02.09, K02.11, K12.03, K13.01 · ➕ K01.03, K01.09, K01.11, K02.07, K02.10, K03.06, K05.11, K13.07, K16.05, K16.07 |
| 15 | Lohnbuchhaltung/Personaldaten | ➕ Lohnjournal-Abstimmung, Mitarbeiterentwicklung | K12.01 · ➕ K09.07, K12.02, K12.05, K12.09, K12.10, K16.04, K17.10 |
| 16/17 | UStVA / USt-Jahreswerte (ZM) | ➕ Erklärungsabgleich | ➕ K10.08, K17.08, K17.10 |
| 18/19 | Vorjahres-/Mehrjahresdaten | Minimum = Vorjahr: ✔ Vorjahres-SuSa (`--susa-vorjahr`) → VJ-01/02, Erlös-Delta; Vorjahres-Buchungsstapel und 2–5 Jahre Zeitreihen ➕ | K01.14, K01.17, K02.12, K06.07, K07.05, K08.05, K08.13, K09.01, K09.02, K12.04, K15.04, K16.09, K17.03, K17.04 · ➕ K04.03, K04.11, K04.13, K05.03, K05.13, K07.02, K08.03, K08.07, K09.04, K09.07, K15.05 |
| 20 | Intercompany-Daten | ➕ Spiegelbild-Abstimmungen | ➕ K04.14, K05.14, K14.01, K17.10 |
| – | Folgeperiode (Folgejahres-Buchungsstapel) | ✔ optional (`--stapel-folgejahr`) → CO-02; erlösseitiger Nachlauf, Zahlungen/Stornos nach Stichtag ➕ bzw. Ausbaustufe | K02.08, K13.01, K13.04, K16.12 · ➕ K04.14, K05.14, K13.03, K16.13, K17.10 |
| – | Kapitalkontenentwicklung, Sonder-/Ergänzungsbilanzen (PersG) | ➕ Mitunternehmer-Prüfungen (§ 15a EStG, Sondervergütungen) | ➕ K08.18, K14.03 |
| – | Verträge/Tilgungspläne (Darlehen, Rückstellungsgründe, Gesellschaftsvertrag) | ➕ Darlehens-/Zinsverprobung, Fristigkeiten, Abzinsung | K08.10, K08.12 · ➕ K08.06, K08.07, K08.09, K17.10 |
| – | Inventur-/Warenwirtschaftsdaten | ➕ Vorräte-Prüfungen (Kap. 7) | ➕ K07.01, K07.02, K07.03, K07.04, K07.07, K13.05, K17.10 |
| – | Positions-Zuordnungstabelle (Konto → Bilanz-/GuV-Position), Anhang-Checkliste | ➕ amtliche Gliederungstiefe § 266/§ 275 HGB, Anhangangaben | K17.02 · ➕ K17.09 |

Katalogpunkte: Soll-IDs, die die Quelle nutzen oder für ihren ➕-Zusatz benötigen; ➕ = offene Punkte (zusätzliche Prüfung/Ausbaustufe), die auf diese Quelle warten.
<!-- KATALOG:SOLL:END -->

## Formatreferenzen (DATEV-Format)

- **[DATEV-Dokument 1003221 – Dateibeschreibung
  DATEV-Format](https://wissensplattform.apps.datev.de/help/document/1003221)**:
  Feldbeschreibungen für Buchungsstapel (Kap. 3, u. a.
  Umsatz/Soll-Haben-Kz/Konto/Gegenkonto/BU-Schlüssel, Belegdatum TTMM),
  wiederkehrende Buchungen (Kap. 4), **Kontenbeschriftungen** (Kap. 5)
  sowie Debitoren-/Kreditorenstammdaten – genau die Formate, die dieser
  Agent liest.
- **[DATEV Developer-Portal:
  DATEV-Format](https://developer.datev.de/de/file-format/details/datev-format/format-description/booking-batch)**
  (Documentation → File Interfaces → DATEV-Format; Detailseiten teils
  erst nach Portal-Anmeldung): Header-Beschreibung mit den
  Datenkategorie-Codes in Header-Feld 3, u. a. **21 = Buchungsstapel**,
  **20 = Kontenbeschriftungen**, 16 = Debitoren-/Kreditorenstammdaten.
- **Selbstauskunft jeder Exportdatei:** Header-Feld 3 (Kategorie) und
  Feld 4 (Formatname) bilden ein Paar, z. B.
  `"EXTF";700;21;"Buchungsstapel";…` bzw.
  `"EXTF";700;20;"Kontenbeschriftungen";…` – der Parser
  (`datev_parser.lies_header`) routet über genau diese Felder.
- Exportwege: SuSa je Geschäftsjahr
  ([Dok. 9304958](https://wissensplattform.apps.datev.de/help/document/9304958),
  [Dok. 9226355](https://wissensplattform.apps.datev.de/help/document/9226355));
  Kontenplan/Kontenbeschriftungen
  ([Dok. 1071499](https://wissensplattform.apps.datev.de/help/document/1071499),
  [Dok. 1036116](https://wissensplattform.apps.datev.de/help/document/1036116)).
- **Wirtschaftsjahr-Anker (CO-01/CO-02, BL-04, PP-02):** Der
  Buchungsstapel-Header führt in Feld 13 den
  **Wirtschaftsjahresbeginn** (JJJJMMTT; Dateibeschreibung Dok. 1003221
  bzw. Developer-Portal, s. o.). WJ-Ende = WJ-Beginn + 12 Monate −
  1 Tag; das WJ kann vom Kalenderjahr abweichen, ein 31.12. wird nie
  unterstellt. Fallback ohne Feld 13: spätestes Header-„Datum bis".
  Die Fensterbreiten `cutoff_fenster_vor_tage`/`cutoff_fenster_nach_tage`
  (je 14 Tage) sind Methodik-Parameter dieses Agenten (fachliche
  Projektvorgabe, konfigurierbar) – keine DATEV- oder Gesetzesvorgabe.

## Kontenzuordnung Eigenkapital (rechtsformabhängig)

Die Bilanz-Positionszuordnung (`werkzeuge/bilanz.py`, Kontengruppen in
`konten_config.json`) gliedert das Eigenkapital rechtsformabhängig;
Bereichsgrenzen sind DATEV-Standard-Startwerte (Leitkonten gequellt,
Unterkonten-Bereiche Konvention – vor Produktiveinsatz gegen den
Kanzlei-Kontenplan prüfen):

- **Kapitalgesellschaft** (§ 266 Abs. 3 A. HGB, Ausweis vor
  Ergebnisverwendung; nach Verwendung träte gemäß § 268 Abs. 1 HGB der
  Bilanzgewinn/-verlust an die Stelle von A.IV/A.V):
  gezeichnetes Kapital SKR03 0800 / SKR04 2900; Kapitalrücklage
  0840–0844 / 2920–2928; Gewinnrücklagen (gesetzliche 0846–0847 /
  2930–2934, Anteile herrschendes Unternehmen 0849–0850 / 2935–2936,
  satzungsmäßige 0851 / 2950–2958, andere 0855, 0848 / 2960–2961);
  Gewinn-/Verlustvortrag vor Verwendung 0860, 0868 / 2970, 2978.
  Quellen: [DATEV Dok. 1029917 – Kapitalgesellschaft:
  Ergebnisverwendung](https://wissensplattform.apps.datev.de/help/document/1029917),
  [Dok. 1040025 – Gewinnrücklage
  buchen](https://wissensplattform.apps.datev.de/help/document/1040025),
  [Dok. 1040067 – Gewinnvortrag oder Verlustvortrag
  buchen](https://wissensplattform.apps.datev.de/help/document/1040067);
  [§ 266 HGB](https://www.gesetze-im-internet.de/hgb/__266.html),
  [§ 268 HGB](https://www.gesetze-im-internet.de/hgb/__268.html).
- **Personengesellschaft** (Kapitalanteile je Haftungsgruppe):
  Festkapital/variables Kapital Vollhafter SKR03 0870/0880 / SKR04
  2000/2010; Kommanditkapital/Verlustausgleichskonto Teilhafter 0900,
  0910 / 2050; Gesellschafter-Darlehen als Fremdkapital 0890/0920;
  Privatkonten Vollhafter 1800–1890, Teilhafter 9400–9490 bzw.
  1900–1990; KKE-/Umbuchungs-/Anteilskonten der Klasse 9 (9141–9189,
  95xx–98xx, 9920 ff.) als Sammelposition „A.VII" (vereinfacht;
  vollständige Kapitalkontenentwicklung ist Ausbaustufe, s. Kap. 8/14).
  Quellen: [DATEV Dok. 1029158 – Kapitalkontenentwicklung (KKE):
  Übersicht der
  Konten](https://wissensplattform.apps.datev.de/help/document/1029158),
  [Dok. 1029213 – Personengesellschaft: Kapitalkonto oder Rücklage
  umbuchen](https://wissensplattform.apps.datev.de/help/document/1029213).
- **Einzelunternehmen:** eine Position „A. Eigenkapital
  (Einzelunternehmen)" inkl. Privatkonten (§ 247 Abs. 1 HGB, keine
  § 266-Untergliederung;
  [§ 247 HGB](https://www.gesetze-im-internet.de/hgb/__247.html)).
- **A.V Jahresüberschuss/Jahresfehlbetrag** ist keinem Konto
  zugeordnet, sondern die GuV-Summe (Excel: Formel auf das GuV-Blatt;
  `salden.csv`: synthetische `(ergebnis)`-Zeile). Die
  **Bilanzprobe** Aktiva − Passiva (inkl. A.V und
  Saldenvortrags-Differenz „Z.") läuft bei jedem Lauf und muss 0,00
  ergeben (Kennzahl im Bericht, stderr-Warnung bei Abweichung).

## Rechtsgrundlagen und Methodik

Normzitate stehen jeweils in der Befund-Empfehlung des Checks; die
vollständige Liste mit Links (AO, HGB, EStG, UStG, GoBD sowie
Nigrini-Benford- und Iglewicz/Hoaglin-MAD-Referenz für ST-08, ST-02,
SB-09) führt die README im Abschnitt „Quellen und Referenzen".

---

## Check-Register (implementierte Klassifikation, generiert)

Quelle: `werkzeuge/befunde.py` (`KATALOG`), Reihenfolge = Katalogreihenfolge.
Ebene 1–4 und Klasse (R/P/A, +X = benötigt Zusatzdaten) sind die Werte, die
Bericht, Excel- und Power-BI-Ausweis je Befund tragen. Nicht von Hand
ändern – `py werkzeuge/katalog_doku.py --write`.

<!-- KATALOG:REGISTER:START -->
| ID | Check | Bereich | Ebene | Klasse | Soll-Punkte | Erwartungsbild (Standard · DQ-02-Lauf · CO-02-Lauf) |
|---|---|---|---|---|---|---|
| DV-01 | Nullbeträge und Konto = Gegenkonto | Datenintegrität | 1 | R (Rule-based) | K01.02, K01.12 | 1 hinweis · = · = |
| DV-02 | EB-Buchungen auf GuV-Konten | Datenintegrität | 1 | R (Rule-based) | K01.15 | 1 mittel · = · = |
| DV-03 | Bebuchte Konten ohne Kontenbeschriftung | Datenintegrität | 1 | R (Rule-based) +X Zusatzdaten | K01.06 | 1 hinweis · = · = |
| DQ-01 | Datenqualität Import | Datenintegrität | 1 | R (Rule-based) | K01.02 | 1 hinweis · = · = |
| DQ-02 | Rechtsform-Konsistenz (Name/Angabe/Kontenbild) | Datenintegrität | 1 | R (Rule-based) | K01.13 | 0 · 2 hoch · = |
| ST-05 | Fehlende Belegnummern/Buchungstexte | Datenintegrität | 1 | P (Plausibilität) | K01.05 | 1 hinweis · = · = |
| ST-06 | Belegdatum außerhalb des Zeitraums | Datenintegrität | 1 | R (Rule-based) | K01.08 | 0 · = · = |
| SB-01 | Negative Kasse | Salden | 2 | R (Rule-based) | K03.01, K03.02 | 1 hoch · = · = |
| SB-02 | Unplausibles Saldenvorzeichen | Salden | 3 | P (Plausibilität) | K06.05, K08.02 | 1 mittel · = · = |
| SB-03 | Geldtransit nicht ausgeglichen | Salden | 2 | R (Rule-based) | K03.13 | 1 mittel · = · = |
| SB-04 | Interims-/Verrechnungskonten nicht ausgeglichen | Salden | 2 | R (Rule-based) | K03.10, K08.15 | 1 mittel · = · = |
| SB-05 | Abweichung zur Summen- und Saldenliste | Salden | 1 | R (Rule-based) +X Zusatzdaten | K17.01 | 1 hinweis · = · = |
| SB-06 | Saldenvorträge saldieren nicht auf null | Salden | 1 | R (Rule-based) | K01.16 | 1 mittel · = · = |
| SB-07 | Ungewöhnlich hoher Kassenbestand | Salden | 3 | P (Plausibilität) | K03.02, K03.03 | 0 · = · = |
| SB-08 | Lücken in der Kassenführung | Salden | 3 | P (Plausibilität) | K02.14, K03.07 | 1 hinweis · = · = |
| SB-09 | Ausreißer-Einzelbewegungen Kasse | Salden | 3 | P (Plausibilität) | K03.04, K03.11 | 2 hinweis · = · = |
| SB-10 | Glatte Barbewegungen Kasse/Privat | Salden | 4 | A (Anomalie) | K03.05, K03.11, K08.16, K11.13 | Skip · 0 · = |
| AF-01 | Anlagenzugänge ohne Abschreibung | AfA | 2 | R (Rule-based) | K06.02 | 0 · = · = |
| AF-02 | Abschreibung ohne Anlagevermögen | AfA | 3 | P (Plausibilität) | K06.03 | 0 · = · = |
| AF-03 | AfA auf nicht abnutzbares Anlagevermögen | AfA | 2 | R (Rule-based) | K06.04 | 1 hoch · = · = |
| AF-04 | GWG-Grenzen | AfA | 2 | R (Rule-based) | K06.09, K06.12 | 1 mittel, 1 hinweis · = · = |
| AF-05 | Aktivierungspflicht-Kandidaten (Instandhaltung) | AfA | 3 | P (Plausibilität) | K06.10 | 1 mittel · = · = |
| US-01 | Vorsteuerschlüssel auf untypischem Konto | USt/VSt | 2 | R (Rule-based) | K10.09 | 1 mittel · = · = |
| US-02 | Direktbuchungen auf Steuerkonten | USt/VSt | 3 | P (Plausibilität) | K10.03, K10.07 | 1 hinweis · = · = |
| US-03 | Ungültige oder historische Steuerschlüssel | USt/VSt | 2 | R (Rule-based) | K01.07, K10.04 | 1 mittel, 1 hinweis · = · = |
| US-04 | Bewirtung ohne nicht abziehbaren Anteil | USt/VSt | 2 | R (Rule-based) | K11.04 | 1 mittel · = · = |
| US-05 | Steuerschlüssel-Abweichler je Sachkonto | USt/VSt | 4 | A (Anomalie) | K10.01, K10.02, K10.05 | 4 hinweis · = · = |
| US-06 | USt-Verprobung (Erlöse) | USt/VSt | 2 | R (Rule-based) +X Zusatzdaten | K10.02, K10.04, K17.07 | 0 · = · = |
| US-07 | VSt-Verprobung (Aufwand) | USt/VSt | 2 | R (Rule-based) +X Zusatzdaten | K10.04, K17.07 | 1 hinweis · = · = |
| US-08 | Steuerschlüssel weicht von Automatikkonto ab | USt/VSt | 2 | R (Rule-based) | K10.01, K10.02 | 1 mittel · = · = |
| US-09 | Steuerschlüssel-Wechsel je Geschäftspartner | USt/VSt | 4 | A (Anomalie) | K10.06 | 1 hinweis · = · = |
| US-10 | Vorsteuerbuchungen ohne Belegnummer | USt/VSt | 3 | P (Plausibilität) | K10.11 | 1 hinweis · = · = |
| RE-01 | Lücken in der Rechnungsnummernfolge | Ausgangsrechnungen | 2 | R (Rule-based) | K01.10 | 1 mittel · = · = |
| RE-02 | Doppelt vergebene Rechnungsnummern | Ausgangsrechnungen | 2 | R (Rule-based) | K02.04 | 1 hoch · = · = |
| RE-03 | Rechnungsdatum entgegen Nummernfolge | Ausgangsrechnungen | 3 | P (Plausibilität) | K02.09 | 1 hinweis · = · = |
| OP-01 | Debitoren mit Habensaldo | OPOS/Kreditoren | 2 | R (Rule-based) | K04.02, K04.07 | 1 mittel · = · = |
| OP-02 | Kreditoren mit Sollsaldo | OPOS/Kreditoren | 2 | R (Rule-based) | K05.02, K05.09, K05.10 | 1 mittel · = · = |
| OP-03 | Überfällige offene Posten | OPOS/Kreditoren | 3 | P (Plausibilität) +X Zusatzdaten | K04.04, K04.08, K05.04 | 2 mittel · = · = |
| OP-04 | Direktverrechnung Debitor/Kreditor | OPOS/Kreditoren | 2 | R (Rule-based) | K04.10 | 1 hinweis · = · = |
| OP-05 | OPOS-Summen weichen vom Kontensaldo ab | OPOS/Kreditoren | 1 | R (Rule-based) +X Zusatzdaten | K04.01, K04.06, K05.01, K17.05 | 3 mittel, 1 hinweis · = · = |
| OP-06 | Alte Kleinstposten und alte Gutschriften | OPOS/Kreditoren | 3 | P (Plausibilität) +X Zusatzdaten | K04.05, K05.04 | 2 hinweis · = · = |
| OP-07 | Konzentration auf einzelne Debitoren | OPOS/Kreditoren | 3 | P (Plausibilität) | K04.12 | 1 hinweis · = · = |
| KR-01 | Gleiche Rechnungsnummer beim selben Kreditor | OPOS/Kreditoren | 2 | R (Rule-based) | K02.04, K05.06 | 1 mittel · = · = |
| BL-01 | Rechnungsabgrenzung ohne Bewegung/Auflösung | Bilanz (sonstige) | 3 | P (Plausibilität) | K08.01, K08.02, K13.06 | 2 hinweis · = · = |
| BL-02 | Rückstellungen ohne jede Bewegung | Bilanz (sonstige) | 3 | P (Plausibilität) | K08.04, K08.05 | 1 hinweis · = · = |
| BL-03 | Darlehen ohne Zinsaufwand | Bilanz (sonstige) | 3 | P (Plausibilität) | K08.10, K08.11 | 0 · = · = |
| BL-04 | Direktbuchungen auf Eigenkapitalkonten | Bilanz (sonstige) | 3 | P (Plausibilität) | K08.14 | 1 hinweis · = · = |
| BL-05 | Latente Steuern (Ansatz und Steuersatz-Staffel) | Bilanz (sonstige) | 3 | P (Plausibilität) +X Zusatzdaten | K08.08 | Skip · = · = |
| VJ-01 | EB-Werte gegen Schlussbilanz des Vorjahres | Vorjahresvergleich | 1 | R (Rule-based) +X Zusatzdaten | K01.14, K01.17, K08.13, K17.03 | 2 mittel, 2 hinweis · = · = |
| VJ-02 | GuV-Konten gegen Vorjahr | Vorjahresvergleich | 3 | P (Plausibilität) +X Zusatzdaten | K06.07, K09.01, K12.04, K17.04 | 3 hinweis · = · = |
| GV-01 | Ungewöhnliche Monatsspitzen je Konto | GuV-Plausibilität | 4 | A (Anomalie) | K02.08, K02.14, K09.02, K09.03, K12.06 | 1 hinweis · = · = |
| GV-02 | Gegenläufige Buchung auf richtungsstabilem Konto | GuV-Plausibilität | 4 | A (Anomalie) | K09.15, K12.07 | 1 hinweis · = · = |
| GV-03 | Seltene Konten-Gegenkonto-Kombination | GuV-Plausibilität | 4 | A (Anomalie) | K02.12, K05.12, K09.08, K09.10, K12.03, K12.08, K16.10 | 2 hinweis · = · = |
| ET-01 | Geschenke über der Abzugsgrenze | Ertragsteuer | 2 | R (Rule-based) | K11.01, K11.12 | 1 mittel · = · = |
| ET-02 | Steuersensible Buchungstexte auf untypischen Konten | Ertragsteuer | 2 | R (Rule-based) | K02.13, K11.02, K11.05, K11.06, K11.07, K11.12 | 1 hinweis · = · = |
| CO-01 | Wesentliche Erlösbuchungen im Cut-off-Fenster vor WJ-Ende | Cut-off | 3 | P (Plausibilität) | K02.08, K09.14, K13.01, K13.02, K16.12 | 1 hinweis · = · = |
| CO-02 | Wesentliche Aufwandsbuchungen im Cut-off-Fenster nach WJ-Ende | Cut-off | 3 | P (Plausibilität) +X Zusatzdaten | K02.08, K13.01, K13.04, K16.12 | Skip · = · 1 hinweis |
| PP-01 | Kfz-Kosten ohne erkennbare Privatnutzung | Personal/Privat | 3 | P (Plausibilität) | K11.08 | Skip · 1 hinweis · = |
| PP-02 | Privatbuchungen nur zum Jahresende | Personal/Privat | 3 | P (Plausibilität) | K08.16, K11.13 | Skip · 1 hinweis · = |
| PP-03 | Lohnaufwand ohne LSt-/SV-Verbindlichkeiten | Personal/Privat | 2 | R (Rule-based) | K12.01 | 1 mittel · = · = |
| PP-04 | Privatkonten bei Kapitalgesellschaft bebucht | Personal/Privat | 2 | R (Rule-based) | K08.17 | 1 mittel · Skip · = |
| GS-01 | Bewegungen auf Gesellschafterkonten | Gesellschafter | 3 | P (Plausibilität) | K08.12, K08.16, K11.08, K11.10, K14.02 | 2 hinweis · = · = |
| ST-01 | Doppelbuchungs-Verdacht | Statistik | 3 | P (Plausibilität) | K02.01, K02.02, K02.03, K02.05, K03.14, K05.05, K05.07, K05.08 | 1 hoch, 2 mittel · = · = |
| ST-02 | Betragsausreißer je Konto | Statistik | 4 | A (Anomalie) | K09.11, K09.14, K10.10, K11.09, K12.06 | 3 mittel · = · = |
| ST-03 | Auffällig runde Beträge | Statistik | 4 | A (Anomalie) | K03.05, K09.13, K16.01 | 2 hinweis · = · = |
| ST-04 | Kassenbuchungen an Sonn- und Feiertagen | Statistik | 4 | A (Anomalie) | K02.11, K16.06 | 1 hinweis · = · = |
| ST-07 | Schwellen-Splitting (GWG-Grenze) | Statistik | 4 | A (Anomalie) | K02.16, K06.09, K06.12, K16.03 | 1 hinweis · = · = |
| ST-08 | Benford-Analyse (erste Ziffer) | Statistik | 4 | A (Anomalie) | K16.02 | 0 · = · = |
| FR-01 | Stornoquote und Storno-Wiederholungen | Fraud-Indikatoren | 4 | A (Anomalie) | K02.06, K16.08 | 0 · = · = |
| FR-02 | Einmal-Kreditoren mit wesentlichem Volumen | Fraud-Indikatoren | 4 | A (Anomalie) | K09.10, K15.04, K16.09 | 1 hinweis · = · = |
| FR-03 | Beträge knapp unter Freigabegrenzen | Fraud-Indikatoren | 3 | P (Plausibilität) +X Zusatzdaten | K02.15, K16.03 | Skip · = · = |
| FR-04 | Häufung glatter Centbeträge (Endziffern) | Fraud-Indikatoren | 4 | A (Anomalie) | K09.13, K16.01 | 0 · = · = |
| SD-01 | Personenkonten mit identischer Bezeichnung | Stammdaten | 3 | P (Plausibilität) +X Zusatzdaten | K15.01, K15.02 | 1 hinweis · = · = |

73 Checks (= `len(befunde.KATALOG)`). Soll-Punkte = Soll-IDs aus `werkzeuge/soll_katalog.json`, die der Check abdeckt; Erwartungsbild = Treffer je Schwere in den drei Referenzläufen aus `testdaten/erwartung.json` („=“ wie Standardlauf, „Skip“ begründet übersprungen, „0“ Nullbefund = geprüft, ohne Befund).
<!-- KATALOG:REGISTER:END -->
