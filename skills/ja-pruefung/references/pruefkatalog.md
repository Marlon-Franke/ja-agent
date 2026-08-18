# Prüfkatalog Jahresabschluss-Agent – Abdeckungsmatrix

Struktur und Klassifikation folgen dem Referenzkatalog
(`Prüfkatalog für einen Python-basierten Accounting-Agenten.md`).

Maßgebliche Zählbasis der Checks ist `befunde.KATALOG`
(`werkzeuge/befunde.py`); die Gesamtzahl-Angaben in README, SKILL.md und
plugin.json folgen `len(befunde.KATALOG)` (Excel-Deckblatt und
stdout-Kopf zählen automatisch).

## Legende

- **[R] Rule-based:** objektiv anhand definierter Regeln prüfbar
- **[P] Plausibilität:** Schwellenwert-/Vergleichsprüfung
- **[A] Anomalie:** statistischer/datengetriebener Auffälligkeitsscore
- **[X] Zusatzdaten:** Prüfung benötigt mehr als den Buchungsstapel

Status je Katalogpunkt:

- **✔ CHECK-ID** – implementiert (deterministisch, `werkzeuge/`)
- **KI** – läuft über die KI-Beurteilungsschicht (Kandidaten-Export)
- **➕ Quelle** – zusätzliche Prüfung: wird aktiv, sobald die genannte
  Datenquelle angeliefert wird (Ausbaustufe, bewusst NICHT „unprüfbar")

## Zielarchitektur: vier Ebenen

Jeder Check trägt eine Ebene (im Bericht ausgewiesen), damit ein
„verdächtig runder Betrag" nie auf derselben Stufe steht wie eine
rechnerisch negative Kasse. Die Tabelle und das Check-Register am Ende
dieser Datei werden aus `befunde.KATALOG` generiert
(`py werkzeuge/katalog_doku.py --write`; der Build prüft die Aktualität).
Die `[R]/[P]/[A]/[X]`-Tags an den Katalogpunkten unten und im README sind
dagegen die Klasse des **Soll-Katalogpunkts** (1:1 aus dem Referenzkatalog);
Ebene und Klasse des **implementierten Checks** stehen allein im Register –
beides darf voneinander abweichen (ein Plausibilitäts-Check kann einen als
[R] klassifizierten Katalogpunkt abdecken):

<!-- KATALOG:EBENEN:START -->
| Ebene | Frage | Checks (Präfixe) |
|---|---|---|
| 1 – technische Integrität | Daten vollständig und konsistent? | DV, DQ, ST-05/06, SB-05/06, OP-05, VJ-01 |
| 2 – Regelprüfung | Verstoß gegen eindeutige Buchungs-/Bilanz-/Steuerregel? | SB-01/03/04, AF-01/03/04, US-01/03/04/06/07/08, RE-01/02, OP-01/02/04, KR, ET, PP-03/04 |
| 3 – Plausibilität | Passt der Sachverhalt zu Schwellen, Struktur, Relationen? | SB-02/07/08/09, AF-02/05, US-02/10, RE-03, OP-03/06/07, BL, VJ-02, CO, PP-01/02, GS, ST-01, FR-03, SD |
| 4 – Anomalie | Statistisch/strukturell ungewöhnlich ohne konkreten Regelverstoß? | SB-10, US-05/09, GV, ST-02/03/04/07/08, FR-01/02/04 |
<!-- KATALOG:EBENEN:END -->

---

## 1. Datenvollständigkeit und technische Integrität

| Katalogpunkt | Status |
|---|---|
| Soll = Haben (Beleg/Periode/Jahr) | strukturell gewährleistet: DATEV-Stapelzeile = Konto+Gegenkonto |
| Buchungen ohne Konto/Gegenkonto/Betrag | ✔ DV-01 + Parser-Abweisungen in DQ-01 |
| Buchungen ohne Belegdatum | ✔ DQ-01 |
| Buchungen ohne Belegnummer/Buchungstext | ✔ ST-05 (Quoten) |
| ungültige/unbekannte Konten | ✔ DV-03 (mit Kontenbeschriftungen) |
| ungültige Steuerschlüssel | ✔ US-03 |
| Buchungen außerhalb WJ / falsche Perioden | ✔ ST-06; Perioden-/Buchungsdatum ➕ GDPdU-Journal |
| Lücken in Beleg-/Buchungsnummern | ✔ RE-01 (Ausgangsrechnungen); Eingangsnummern bewusst nicht (fremdvergeben) |
| identische technische Buchungs-IDs | ➕ Journal-Export mit IDs |
| inkonsistente Datensätze | ✔ DV-01 (Konto = Gegenkonto) |
| Rechtsform-Konsistenz (Mandantenname ↔ Angabe ↔ Kontenbild) | ✔ DQ-02 (Klassifizierung: `rechtsformen_erkennung` in konten_config.json; KSt-/gez.-Kapital- vs. Privatkonten-Indizien; § 1a-KStG-Vorbehalt) |
| EB = Schlussbilanz Vorjahr, EB je Konto | ✔ VJ-01 (mit Vorjahres-SuSa, `--susa-vorjahr`) |
| keine EB-Buchungen auf GuV-Konten | ✔ DV-02 |
| neue/verschwundene Bilanzkonten | ✔ VJ-01 |
| Saldenvorträge saldieren auf 0 | ✔ SB-06 |

## 2. Journal- und Buchungsprüfung

| Katalogpunkt | Status |
|---|---|
| exakt identische Doppelbuchungen | ✔ ST-01 (hoch bei identischem Beleg) |
| wahrscheinliche Doppelbuchungen | ✔ ST-01 (Zeitfenster) + KI |
| gleiche Rechnungsnummer mehrfach | ✔ RE-02 (Ausgang), ✔ KR-01 (Eingang je Kreditor) |
| Buchung und Storno ohne Anlass / Mehrfachstorno | ✔ FR-01 |
| viele manuelle/Nachtrags-/Abschlussbuchungen | ✔ GV-01, CO-01/CO-02; Erfassungsart ➕ Journal |
| rückdatierte Buchungen, Beleg-/Buchungsdatum-Abstand | ✔ RE-03 (Indiz); vollständig ➕ Journal mit Erfassungsdatum |
| ungewöhnliche Tage/Uhrzeiten/Benutzer | ✔ ST-04 (Belegdatum, Kasse); Uhrzeit/User ➕ Journal |
| ungewöhnliche Konten-Gegenkonto-Kombination / erstmalige Kontierung | ✔ GV-03; jahresübergreifend ➕ Vorjahr |
| ungewöhnliche Buchungstexte | KI (Kandidaten) + ✔ ET-02 (Textmuster regelbasiert) |
| Beträge knapp an Freigabegrenzen / Betragsaufteilung | ✔ FR-03 (konfigurierbar), ✔ ST-07 |

## 3. Kasse und liquide Mittel

| Katalogpunkt | Status |
|---|---|
| negativer Kassenbestand (§ 146 AO) | ✔ SB-01 (taggenauer Verlauf) |
| hohe Kassenbestände | ✔ SB-07 |
| hohe Bareinzahlungen/-entnahmen, sprunghafte Änderungen | ✔ SB-09 |
| viele glatte Bargeldbeträge | ✔ SB-10 (Kasse↔Privat), ✔ ST-03 |
| nachträgliche Kassenbuchungen | ➕ Journal mit Erfassungsdatum |
| zeitliche Lücken in der Kassenführung | ✔ SB-08 |
| Geldtransit gleicht sich zum Stichtag aus (Einzahlung unterwegs) | ✔ SB-03 |
| Kassenbuch gegen FIBU | ➕ Kassenbuch-Export |
| Bank: Saldo/Bewegungen gegen Kontoauszug, ungeklärte Posten, Transfers | ➕ Bankauszüge (CAMT/CSV) |
| gleiche Zahlung mehrfach verbucht | ✔ ST-01 |

## 4. Debitoren und Forderungen

| Katalogpunkt | Status |
|---|---|
| Hauptbuch = Nebenbuch | ✔ OP-05 (OPOS-Summen je Konto) |
| Kreditsalden auf Debitoren | ✔ OP-01 |
| überfällige Forderungen, Altersstruktur 30/60/90/180/365 | ✔ OP-03 + Blatt „OPOS-Alterung" |
| alte Kleinstbeträge / alte Gutschriften | ✔ OP-06 |
| Zahlung ohne Forderung | ✔ OP-01 |
| Verrechnung zwischen Personenkonten | ✔ OP-04 |
| Konzentrationsrisiko | ✔ OP-07 |
| ausgeglichene Rechnungen als offen, doppelte offene Posten, Teilzahlungen | ➕ OPOS-Detail mit Ausgleichsinfo |
| Zahlungsverhalten je Kunde, Forderung vs. Umsatzentwicklung | ➕ Vorjahresdaten |
| Zahlungseingänge nach Stichtag, Mahnstatus, EWB gegen Alter, verbundene Unternehmen | ➕ Folgeperiode/Mahnwesen/Kontenzuordnung |

## 5. Kreditoren und Verbindlichkeiten

| Katalogpunkt | Status |
|---|---|
| Hauptbuch = Nebenbuch | ✔ OP-05 |
| Sollsalden auf Kreditoren | ✔ OP-02 |
| alte Verbindlichkeiten/Gutschriften | ✔ OP-03, OP-06 |
| identische Eingangsrechnung mehrfach | ✔ ST-01 |
| gleiche Rechnungsnummer beim Kreditor | ✔ KR-01 |
| doppelte Zahlungen | ✔ ST-01; gegen Bank ➕ Bankauszüge |
| Zahlung ohne Verbindlichkeit | ✔ OP-02 |
| ungewöhnliches Kreditorenkonto je Kostenart | ✔ GV-03 |
| Zahlungsprofil-Änderung, Vorauszahlungen, nach Stichtag, verbundene | ➕ Vorjahr/Folgeperiode |

## 6. Anlagevermögen und AfA

| Katalogpunkt | Status |
|---|---|
| Sachkonten/AfA/Zu-/Abgänge = Anlagenbuchhaltung | ➕ Anlagenspiegel-Export |
| Wirtschaftsgut ohne AfA (global) | ✔ AF-01 |
| AfA ohne Anlagevermögen | ✔ AF-02 |
| AfA auf nicht abnutzbares AV (Grund und Boden) | ✔ AF-03 |
| negativer Buchwert | ✔ SB-02 |
| je Wirtschaftsgut: AfA > Restwert, nach Abgang, ND, Methode, zeitanteilig | ➕ Anlagenspiegel |
| GWG-/Sammelpostenbehandlung | ✔ AF-04 (Grenzen), ✔ ST-07 (Splitting) |
| größere Anschaffungen direkt als Aufwand | ✔ AF-05 + KI (alle wesentlichen Aufwands-Einzelbuchungen als Kandidaten) |
| laufende Aufwendungen unplausibel aktiviert | KI (AV-Zugänge in Kandidatenlage) |
| außerplanmäßige AfA, Abgangsergebnis | ➕ Anlagenspiegel/Belege |

## 7. Vorräte und Waren

| Katalogpunkt | Status |
|---|---|
| Warenaufwand vs. Umsatz (Rohertrag) | ✔ Kennzahlen-Ausweis (Material-/Rohertragsquote) |
| Buchungen auf Bestandskonten vor Stichtag | ✔ CO-01 (erlös-/forderungsseitig vor WJ-Ende); aufwandsseitiger Nachlauf ✔ CO-02 (`--stapel-folgejahr`) |
| Inventur, Mengen, Reichweiten, Niederstwert | ➕ Inventur-/Warenwirtschaftsdaten |

## 8. Sonstige Bilanzkonten

| Katalogpunkt | Status |
|---|---|
| wiederkehrende Zahlungen ohne RAP / ARAP bzw. PRAP nicht aufgelöst (je Richtung, § 250 HGB) | ✔ BL-01; Vorzeichen ✔ SB-02 |
| RAP-Alter, RAP-Veränderung | ➕ Vorjahresdaten |
| Rückstellung ohne Bewegung | ✔ BL-02 |
| jährlich identische Rückstellungsbeträge | ✔ BL-02 (mit `--susa-vorjahr`) |
| Rückstellungs-Schwankungen, Abzinsung | ➕ Vorjahr/Verträge |
| latente Steuern: Bestand/Ansatz, Steuersatz-Staffel (KSt-Senkung ab 2028, § 274/274a HGB) | ✔ BL-05 (Gruppe `latente_steuern` konfigurieren); Differenzenrechnung ➕ Steuerbilanz/Überleitung |
| Darlehen ohne Zinsbuchung | ✔ BL-03 |
| Darlehen gegen Tilgungsplan, Zinssatz-Verprobung, Fristigkeiten | ➕ Darlehensverträge |
| Direktbuchungen auf EK-Konten, unterjährig auf Gewinnvortrag | ✔ BL-04 |
| Interims-/Verrechnungs- und durchlaufende Konten zum Stichtag ausgeglichen | ✔ SB-04 |
| Vortrag Vorjahr, Ergebnisverwendung | ➕ Vorjahresdaten |
| ungewöhnliche Einlagen/Entnahmen | ✔ PP-02, SB-10, GS-01 |
| Privatkonten bei Kapitalgesellschaft | ✔ PP-04 (mit `--rechtsform`; PP-01/02, SB-10 werden bei KapG begründet übersprungen) |
| Kapitalkontenentwicklung je Gesellschafter, § 15a EStG (PersG) | ➕ Kapitalkontenentwicklung/Gesellschaftsvertrag |

## 9. GuV- und Kontenplausibilitäten

| Katalogpunkt | Status |
|---|---|
| Konto gegen Vorjahr: Veränderung, Vorzeichenwechsel, erstmalig/weggefallen | ✔ VJ-02 (mit `--susa-vorjahr`); Vorperioden des VJ ➕ Vorjahres-Stapel |
| Monatsverlauf, Monatsspitzen | ✔ GV-01 |
| Verhältniskennzahlen (Material-, Personal-, Mietkosten-, Werbekostenquote, Rohertrag) | ✔ Kennzahlen-Ausweis; Kfz bewusst nicht als Quote (PP-01/ST-02); weitere Quoten ➕ Kontenzuordnung/Vorjahr |
| ungewöhnliche Gegenkonten | ✔ GV-03 |
| sachfremde Buchungstexte | KI (Kandidaten) |
| hohe Einzelbuchungen | ✔ ST-02 |
| viele glatte Beträge | ✔ ST-03, FR-04 |
| außergewöhnliche Beträge kurz vor Periodenende | ✔ CO-01 (Erlösseite); betragsgroße Einzelfälle zudem ST-02 |
| Gegenbuchungen auf einseitigen Konten / hohe Gutschriften | ✔ GV-02 |

## 10. Umsatzsteuer

| Katalogpunkt | Status |
|---|---|
| Erlös-/Aufwandskonto ↔ Steuerschlüssel plausibel | ✔ US-05 (Profil), ✔ US-08 (Automatikkonflikt) |
| USt-Verprobung: rechnerische USt (Erlöse/Schlüssel) ↔ Steuerkonten | ✔ US-06 (mit SuSa), Konfiguration `steuerschluessel` |
| VSt-Verprobung: rechnerische VSt (Aufwand/Schlüssel) ↔ Steuerkonten | ✔ US-07 (mit SuSa) |
| Schlüssel je Partner verändert | ✔ US-09 |
| falsches Vorzeichen auf Steuerkonten | ✔ GV-02, ✔ US-02 |
| USt-Konten gegen UStVA/Jahreserklärung | ➕ UStVA-/Erklärungswerte |
| VSt auf eingeschränkt abzugsfähigen Konten | ✔ US-01 |
| ungewöhnlich hohe VSt-Beträge | ✔ ST-02 |
| VSt ohne Beleg-/Kreditorbezug | ✔ US-10 |
| Rechnungsangaben §§ 14, 14a UStG, Leistungsbezug | ➕ digitale Belege |
| Reverse Charge § 13b, EU-Sachverhalte, ZM/Intrastat | ➕ EU-/13b-Schlüsselkatalog + Stammdaten (Ausbaustufe; Stapel-Felder vorhanden) |
| Berichtigungen § 17 (Gutschrift/Skonto/Boni, Uneinbringlichkeit), § 15a, § 14c | ➕ Skonto-Feld-Auswertung, OPOS-Historie, Belege |

## 11. Ertragsteuerliche Auffälligkeiten

| Katalogpunkt | Status |
|---|---|
| Geschenke über Grenze / falsches Konto | ✔ ET-01 (35/50 EUR nach WJ-Beginn; Maßstab netto, ohne VSt-Abzug brutto: `vst_abzugsberechtigt`), ✔ ET-02 (Muster „Geschenk") |
| Geschenke-Summe je Empfänger und Jahr gegen die Freigrenze | ➕ Empfängeraufzeichnung (§ 4 Abs. 7 EStG) |
| Bewirtung unplausibel | ✔ US-04 (fehlender 30-%-Anteil = mittel; Quote unter `bewirtung_nabz_quote_min` = Hinweis) |
| Geldbußen/Ordnungsgelder als abziehbar | ✔ ET-02 (Muster) |
| Gewerbesteuer als abziehbar | ✔ ET-02 (Muster) |
| Spenden auf Werbekonten | ✔ ET-02 (Muster) |
| private/gesellschaftsnahe Aufwendungen | KI (Kandidaten) + ✔ GS-01 |
| hohe Reise-/Fahrzeug-/Repräsentationskosten | ✔ Kennzahlen + ST-02 + KI |
| vGA-Sachverhalte (Review-Hinweis) | KI (Urteil mit Begründung) |
| getrennte Aufzeichnung § 4 Abs. 7 EStG | ✔ in Empfehlungenstexten ET-01/02 |
| ungewöhnliche Privatkontenbewegungen | ✔ PP-02, SB-10 |

## 12. Lohn- und Personalverrechnung

| Katalogpunkt | Status |
|---|---|
| LSt-/SV-Verbindlichkeiten bebucht | ✔ PP-03 (Minimum) |
| Lohnjournal gegen FIBU, Verbindlichkeiten gegen Abrechnung | ➕ Lohnjournal/Buchungsbeleg |
| negative Lohnaufwendungen | ✔ GV-02 |
| Zahlungen außerhalb üblicher Lohnkonten | ✔ GV-03 (z. B. Barlohn) |
| Personalkosten vs. Mitarbeiterentwicklung, Rückstellungen Urlaub/Boni | ➕ Personaldaten/Vorjahr |

## 13. Periodenabgrenzung und Cut-off

| Katalogpunkt | Status |
|---|---|
| große Erlösbuchungen im Fenster vor WJ-Ende (Umsatzrealisierung) | ✔ CO-01 – Fenster `cutoff_fenster_vor_tage` (14 Tage) strikt vor dem WJ-Ende aus dem DATEV-Header (WJ ≠ Kalenderjahr möglich, nie 31.12. hartkodiert) |
| große Aufwandsbuchungen im Fenster nach WJ-Ende (Vollständigkeit der Verbindlichkeiten, verspätete ER) | ✔ CO-02 [X] – Fenster `cutoff_fenster_nach_tage` (14 Tage); Datenquelle optionaler Folgejahres-Stapel (`--stapel-folgejahr`), ohne Lieferung begründeter Skip (kein Mangel, der Prüfjahres-Stapel endet am WJ-Ende) |
| wiederkehrende Jahreskosten ohne Abgrenzung | ✔ BL-01 |
| Stornos nach Stichtag, Rechnungs- vs. Buchungsdatum über Jahresgrenze | ➕ Folgeperioden-Journal mit Erfassungsdatum |
| Leistungsdatum gegen Periode, Wareneingang gegen ER | ➕ Belege/Warenwirtschaft; KI-Beurteilung der CO-01/CO-02-Kandidaten nutzt den Buchungstext als Leistungsdatum-Indiz |

## 14. Intercompany und Gesellschafter

| Katalogpunkt | Status |
|---|---|
| Bewegungen/Salden auf Gesellschafterkonten, privat wirkende Aufwendungen | ✔ GS-01 + KI |
| Spiegelbild-Abstimmung (Forderung A = Verbindlichkeit B, Zins/Zins) | ➕ Daten der Gegenseite |
| Sonder-/Ergänzungsbilanzen, Sondervergütungen (§ 15 Abs. 1 S. 1 Nr. 2 EStG) | ➕ Sonder-/Ergänzungsbilanzen bzw. Gewinnfeststellung |

## 15. Stammdatenprüfung

| Katalogpunkt | Status |
|---|---|
| identische Kunden/Lieferanten mehrfach | ✔ SD-01 (Bezeichnungen) |
| neue Kreditoren mit hohem Volumen / Einmal-Lieferanten | ✔ FR-02 |
| IBAN-Dubletten, Adressen, Bankverbindungs-Änderungen, Pflichtfelder | ➕ Stammdaten-Export (Debitoren/Kreditoren) |

## 16. Fraud-/Forensic-Indikatoren

Nur Risikosignale, keine Fehlernachweise (Ausweis als „hinweis" auf Ebene 4).

| Katalogpunkt | Status |
|---|---|
| runde Beträge / Endziffern-Häufung | ✔ ST-03, ✔ FR-04 |
| Benford-Screening | ✔ ST-08 (ab `benford_min_n` GuV-Buchungen, Default 300 – konservative eigene Kalibrierung, siehe README „Methodik") |
| Beträge knapp unter Freigabegrenzen / Aufteilung | ✔ FR-03, ✔ ST-07 |
| Wochenend-/Feiertagsbuchungen | ✔ ST-04 (Kasse, Belegdatum; bundeseinheitliche Feiertage, Landesfeiertage über `feiertage_zusatz`) |
| hohe Storno-/Korrekturquote | ✔ FR-01 |
| Einmal-Lieferanten, neue Lieferanten vor großen Zahlungen | ✔ FR-02 |
| ungewöhnliche Kontierungswege/Freitexte | ✔ GV-03 + KI |
| Buchungen unmittelbar vor Abschluss | ✔ CO-01 (erlösseitig), ✔ CO-02 (aufwandsseitig nach WJ-Ende, fakultativ) |
| User-/Uhrzeit-/IBAN-Muster, Storno nach Stichtag | ➕ Journal mit User/Zeit, Stammdaten, Folgeperiode |

## 17. Gesamtabschluss und Cross-Checks

| Querverprobung | Status |
|---|---|
| Stapel ↔ Summen- und Saldenliste | ✔ SB-05 |
| Umsatzsteuerkonten ↔ rechnerische USt/VSt | ✔ US-06, ✔ US-07 |
| Sachkonten ↔ OPOS-Nebenbuch | ✔ OP-05 |
| OPOS ↔ Altersstruktur | ✔ Blatt „OPOS-Alterung" |
| Schlussbilanz Vorjahr ↔ Eröffnungsbilanz | ✔ VJ-01 |
| GuV-Vorjahresvergleich je Konto | ✔ VJ-02 |
| Stapel ↔ ausgewiesene Bilanz-/GuV-Positionen (Gliederung § 266/§ 275 HGB) | ➕ Positions-Zuordnungstabelle |
| Anhangangaben, größenabhängige Erleichterungen (§§ 284–288, 274a, 276 HGB) | ➕ Anhang-Checkliste; Größenklassen-Indikation § 267/267a ✔ Kennzahl (ohne Ø-AN-Zahl) |
| Anlagen-/Lohnbuchhaltung, Bank, Kassenbuch, UStVA, ZM, Inventur, Verträge, IC | ➕ jeweilige Datenquelle (siehe 20.) |

## 18. Kontenspezifische Erwartungslogik

Teilweise umgesetzt über Kontengruppen-Erwartungen in
`konten_config.json` (erwartetes Vorzeichen → SB-02; übliche
Steuerschlüssel → US-05/08/09 dynamisch; Betragsbandbreite → ST-02
dynamisch; Buchungsfrequenz → SB-08; erlaubte Themen → ET-02).
Ausbaustufe: optionales `erwartungen`-Objekt je Einzelkonto
(Gegenkonten-Whitelist, Monatsverteilung, Vorjahresabweichung)
– Struktur siehe Referenzkatalog Kap. 18.

## 19. Ergebnisstruktur

Jeder Befund führt: Check-ID, Prüfbereich, **Ebene (1–4)**, **Klasse
(R/P/A/X)**, Schwere, Konto, Gegenkonto, Datum, Betrag, Beleg,
Buchungstext, Befundtext (erwarteter/tatsächlicher Zustand), Empfehlung
(vorgeschlagene Prüfhandlung), Quelle (Datei:Zeile), KI-Kennzeichen –
plus leere **Review-Spalten (Status, Bearbeiter, Kommentar)** im Excel.
Die KI-Schicht ergänzt Urteil, Begründung, Schwere und **Konfidenz** je
Kandidat. Noch offen (Ausbaustufe): Regelversion je Check,
Wesentlichkeitsbezug zur Bilanzsumme.

## 20. Datenquellen

| Quelle | Status im Agenten |
|---|---|
| 1. Buchungsstapel (EXTF/DTVF Kat. 21) | ✔ Pflichtquelle |
| 2. SuSa | ✔ optional (`--susa`) → SB-05, US-06/07 |
| 3. Kontenplan des Mandanten (= Kontenbeschriftungen, Kat. 20: angelegte Konten + Bezeichnungen) | ✔ optional (automatisch erkannt bzw. `--kontenplan`) → DV-03, SD-01, Nutzungsgrad-Kennzahl |
| 4./5. Debitoren-/Kreditorenstammdaten | ➕ schaltet IBAN-/Adress-/Dubletten-Prüfungen frei |
| 6./7. OPOS Debitoren/Kreditoren | ✔ optional (`--opos`) → OP-03/05/06, Alterung |
| 8. Anlagenbuchhaltung | ➕ schaltet AfA-Einzelprüfungen je Wirtschaftsgut frei |
| 9. Bankbewegungen | ➕ Bankabstimmung, Zahlungsabgleich |
| 10. Kassenbewegungen/Kassenbuch | ➕ Kassenbuch-Abstimmung |
| 11. digitale Belege | ➕ §§ 14/15-Rechnungsprüfung |
| 12. Steuerschlüssel-Katalog | ✔ `konten_config.json` (erweiterbar) |
| 13. Kostenstellen/Kostenträger | optional (nicht unverzichtbar) – Feld wird gelesen; KOST-Auswertung Ausbaustufe |
| 14. Benutzer-/Erfassungsinfos | ➕ Journal (GDPdU) → User-/Zeit-/Rückdatierungs-Checks |
| 15. Lohnbuchhaltung | ➕ Lohnjournal-Abstimmung |
| 16./17. UStVA/USt-Jahreswerte | ➕ Erklärungsabgleich |
| 18./19. Vorjahres-/Mehrjahresdaten | Minimum = Vorjahr: ✔ Vorjahres-SuSa (`--susa-vorjahr`) → VJ-01/02, Erlös-Delta; 2–5 Jahre Zeitreihen ➕ |
| 20. Intercompany-Daten | ➕ Spiegelbild-Abstimmungen |
| Kapitalkontenentwicklung, Sonder-/Ergänzungsbilanzen (PersG) | ➕ Mitunternehmer-Prüfungen (§ 15a EStG, Sondervergütungen) |

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
| ID | Check | Bereich | Ebene | Klasse |
|---|---|---|---|---|
| DV-01 | Nullbeträge und Konto = Gegenkonto | Datenintegrität | 1 | R (Rule-based) |
| DV-02 | EB-Buchungen auf GuV-Konten | Datenintegrität | 1 | R (Rule-based) |
| DV-03 | Bebuchte Konten ohne Kontenbeschriftung | Datenintegrität | 1 | R (Rule-based) +X Zusatzdaten |
| DQ-01 | Datenqualität Import | Datenintegrität | 1 | R (Rule-based) |
| DQ-02 | Rechtsform-Konsistenz (Name/Angabe/Kontenbild) | Datenintegrität | 1 | R (Rule-based) |
| ST-05 | Fehlende Belegnummern/Buchungstexte | Datenintegrität | 1 | P (Plausibilität) |
| ST-06 | Belegdatum außerhalb des Zeitraums | Datenintegrität | 1 | R (Rule-based) |
| SB-01 | Negative Kasse | Salden | 2 | R (Rule-based) |
| SB-02 | Unplausibles Saldenvorzeichen | Salden | 3 | P (Plausibilität) |
| SB-03 | Geldtransit nicht ausgeglichen | Salden | 2 | R (Rule-based) |
| SB-04 | Interims-/Verrechnungskonten nicht ausgeglichen | Salden | 2 | R (Rule-based) |
| SB-05 | Abweichung zur Summen- und Saldenliste | Salden | 1 | R (Rule-based) +X Zusatzdaten |
| SB-06 | Saldenvorträge saldieren nicht auf null | Salden | 1 | R (Rule-based) |
| SB-07 | Ungewöhnlich hoher Kassenbestand | Salden | 3 | P (Plausibilität) |
| SB-08 | Lücken in der Kassenführung | Salden | 3 | P (Plausibilität) |
| SB-09 | Ausreißer-Einzelbewegungen Kasse | Salden | 3 | P (Plausibilität) |
| SB-10 | Glatte Barbewegungen Kasse/Privat | Salden | 4 | A (Anomalie) |
| AF-01 | Anlagenzugänge ohne Abschreibung | AfA | 2 | R (Rule-based) |
| AF-02 | Abschreibung ohne Anlagevermögen | AfA | 3 | P (Plausibilität) |
| AF-03 | AfA auf nicht abnutzbares Anlagevermögen | AfA | 2 | R (Rule-based) |
| AF-04 | GWG-Grenzen | AfA | 2 | R (Rule-based) |
| AF-05 | Aktivierungspflicht-Kandidaten (Instandhaltung) | AfA | 3 | P (Plausibilität) |
| US-01 | Vorsteuerschlüssel auf untypischem Konto | USt/VSt | 2 | R (Rule-based) |
| US-02 | Direktbuchungen auf Steuerkonten | USt/VSt | 3 | P (Plausibilität) |
| US-03 | Ungültige oder historische Steuerschlüssel | USt/VSt | 2 | R (Rule-based) |
| US-04 | Bewirtung ohne nicht abziehbaren Anteil | USt/VSt | 2 | R (Rule-based) |
| US-05 | Steuerschlüssel-Abweichler je Sachkonto | USt/VSt | 4 | A (Anomalie) |
| US-06 | USt-Verprobung (Erlöse) | USt/VSt | 2 | R (Rule-based) +X Zusatzdaten |
| US-07 | VSt-Verprobung (Aufwand) | USt/VSt | 2 | R (Rule-based) +X Zusatzdaten |
| US-08 | Steuerschlüssel weicht von Automatikkonto ab | USt/VSt | 2 | R (Rule-based) |
| US-09 | Steuerschlüssel-Wechsel je Geschäftspartner | USt/VSt | 4 | A (Anomalie) |
| US-10 | Vorsteuerbuchungen ohne Belegnummer | USt/VSt | 3 | P (Plausibilität) |
| RE-01 | Lücken in der Rechnungsnummernfolge | Ausgangsrechnungen | 2 | R (Rule-based) |
| RE-02 | Doppelt vergebene Rechnungsnummern | Ausgangsrechnungen | 2 | R (Rule-based) |
| RE-03 | Rechnungsdatum entgegen Nummernfolge | Ausgangsrechnungen | 3 | P (Plausibilität) |
| OP-01 | Debitoren mit Habensaldo | OPOS/Kreditoren | 2 | R (Rule-based) |
| OP-02 | Kreditoren mit Sollsaldo | OPOS/Kreditoren | 2 | R (Rule-based) |
| OP-03 | Überfällige offene Posten | OPOS/Kreditoren | 3 | P (Plausibilität) +X Zusatzdaten |
| OP-04 | Direktverrechnung Debitor/Kreditor | OPOS/Kreditoren | 2 | R (Rule-based) |
| OP-05 | OPOS-Summen weichen vom Kontensaldo ab | OPOS/Kreditoren | 1 | R (Rule-based) +X Zusatzdaten |
| OP-06 | Alte Kleinstposten und alte Gutschriften | OPOS/Kreditoren | 3 | P (Plausibilität) +X Zusatzdaten |
| OP-07 | Konzentration auf einzelne Debitoren | OPOS/Kreditoren | 3 | P (Plausibilität) |
| KR-01 | Gleiche Rechnungsnummer beim selben Kreditor | OPOS/Kreditoren | 2 | R (Rule-based) |
| BL-01 | Rechnungsabgrenzung ohne Bewegung/Auflösung | Bilanz (sonstige) | 3 | P (Plausibilität) |
| BL-02 | Rückstellungen ohne jede Bewegung | Bilanz (sonstige) | 3 | P (Plausibilität) |
| BL-03 | Darlehen ohne Zinsaufwand | Bilanz (sonstige) | 3 | P (Plausibilität) |
| BL-04 | Direktbuchungen auf Eigenkapitalkonten | Bilanz (sonstige) | 3 | P (Plausibilität) |
| BL-05 | Latente Steuern (Ansatz und Steuersatz-Staffel) | Bilanz (sonstige) | 3 | P (Plausibilität) +X Zusatzdaten |
| VJ-01 | EB-Werte gegen Schlussbilanz des Vorjahres | Vorjahresvergleich | 1 | R (Rule-based) +X Zusatzdaten |
| VJ-02 | GuV-Konten gegen Vorjahr | Vorjahresvergleich | 3 | P (Plausibilität) +X Zusatzdaten |
| GV-01 | Ungewöhnliche Monatsspitzen je Konto | GuV-Plausibilität | 4 | A (Anomalie) |
| GV-02 | Gegenläufige Buchung auf richtungsstabilem Konto | GuV-Plausibilität | 4 | A (Anomalie) |
| GV-03 | Seltene Konten-Gegenkonto-Kombination | GuV-Plausibilität | 4 | A (Anomalie) |
| ET-01 | Geschenke über der Abzugsgrenze | Ertragsteuer | 2 | R (Rule-based) |
| ET-02 | Steuersensible Buchungstexte auf untypischen Konten | Ertragsteuer | 2 | R (Rule-based) |
| CO-01 | Wesentliche Erlösbuchungen im Cut-off-Fenster vor WJ-Ende | Cut-off | 3 | P (Plausibilität) |
| CO-02 | Wesentliche Aufwandsbuchungen im Cut-off-Fenster nach WJ-Ende | Cut-off | 3 | P (Plausibilität) +X Zusatzdaten |
| PP-01 | Kfz-Kosten ohne erkennbare Privatnutzung | Personal/Privat | 3 | P (Plausibilität) |
| PP-02 | Privatbuchungen nur zum Jahresende | Personal/Privat | 3 | P (Plausibilität) |
| PP-03 | Lohnaufwand ohne LSt-/SV-Verbindlichkeiten | Personal/Privat | 2 | R (Rule-based) |
| PP-04 | Privatkonten bei Kapitalgesellschaft bebucht | Personal/Privat | 2 | R (Rule-based) |
| GS-01 | Bewegungen auf Gesellschafterkonten | Gesellschafter | 3 | P (Plausibilität) |
| ST-01 | Doppelbuchungs-Verdacht | Statistik | 3 | P (Plausibilität) |
| ST-02 | Betragsausreißer je Konto | Statistik | 4 | A (Anomalie) |
| ST-03 | Auffällig runde Beträge | Statistik | 4 | A (Anomalie) |
| ST-04 | Kassenbuchungen an Sonn- und Feiertagen | Statistik | 4 | A (Anomalie) |
| ST-07 | Schwellen-Splitting (GWG-Grenze) | Statistik | 4 | A (Anomalie) |
| ST-08 | Benford-Analyse (erste Ziffer) | Statistik | 4 | A (Anomalie) |
| FR-01 | Stornoquote und Storno-Wiederholungen | Fraud-Indikatoren | 4 | A (Anomalie) |
| FR-02 | Einmal-Kreditoren mit wesentlichem Volumen | Fraud-Indikatoren | 4 | A (Anomalie) |
| FR-03 | Beträge knapp unter Freigabegrenzen | Fraud-Indikatoren | 3 | P (Plausibilität) +X Zusatzdaten |
| FR-04 | Häufung glatter Centbeträge (Endziffern) | Fraud-Indikatoren | 4 | A (Anomalie) |
| SD-01 | Personenkonten mit identischer Bezeichnung | Stammdaten | 3 | P (Plausibilität) +X Zusatzdaten |

73 Checks (= `len(befunde.KATALOG)`).
<!-- KATALOG:REGISTER:END -->
