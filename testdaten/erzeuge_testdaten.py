"""Erzeugt synthetische DATEV-Demodaten (SKR03, WJ 2025) mit gezielt
eingebauten Fehlerbildern fuer die Checks der Pruefpipeline.

Ausgaben (im Ordner testdaten/):
  EXTF_Buchungsstapel_2025_Demo.csv   Buchungsstapel (Kat. 21)
  EXTF_Kontenbeschriftungen_Demo.csv  Kontenbeschriftungen (Kat. 20)
  SuSa_2025_Demo.csv                  SuSa mit 2 gewollten Abweichungen
  OPOS_2025_Demo.csv                  OPOS-Liste mit Altposten/Gutschrift
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ZIEL = Path(__file__).parent
D = Decimal

BUCHUNGEN: list[tuple] = []  # (umsatz, sh, konto, gegenkonto, bu, datum, beleg, text)


def buche(umsatz, sh, konto, gegen, datum, text, bu="", beleg=""):
    BUCHUNGEN.append((D(str(umsatz)), sh, konto, gegen, bu, datum, beleg, text))


# --- Eroeffnungsbilanz (SB-06: Vortraege saldieren bewusst NICHT auf 0) ---
buche(2000, "S", 1000, 9000, date(2025, 1, 1), "EB Kasse")
buche(45000, "S", 1200, 9000, date(2025, 1, 1), "EB Bank")
buche(18000, "S", 320, 9000, date(2025, 1, 1), "EB Pkw")
buche(80000, "S", 65, 9000, date(2025, 1, 1), "EB Grundstück")
buche(3570, "S", 10001, 9000, date(2025, 1, 1), "EB Forderung Alpha")
buche(1200, "S", 980, 9000, date(2025, 1, 1), "EB aktive Rechnungsabgrenzung")   # BL-01
buche(5950, "S", 9000, 70001, date(2025, 1, 1), "EB Verbindlichkeit Delta")
buche(5000, "S", 9000, 970, date(2025, 1, 1), "EB Sonstige Rückstellungen")      # BL-02
buche(300, "S", 9000, 4210, date(2025, 1, 1), "EB-Übernahme fehlerhaft")         # DV-02
# Eigenkapital-Gliederung der GmbH (§ 266 Abs. 3 A HGB); Summe 137.520,
# Vorjahres-Schlussbestand 138.520 -> 1.000 Differenz im Gewinnvortrag (VJ-01)
buche(25000, "S", 9000, 800, date(2025, 1, 1), "EB Gezeichnetes Kapital")
buche(30000, "S", 9000, 840, date(2025, 1, 1), "EB Kapitalrücklage")
buche(82520, "S", 9000, 860, date(2025, 1, 1), "EB Gewinnvortrag")

# --- Ausgangsrechnungen: Debitor an 8400 (Automatik 19 %) ------------------
# RE-01: Nr. 105 fehlt | RE-02: Nr. 108 doppelt | RE-03: 110 datiert vor 109
# CO-01: Nr. 113 am 30.12. ueber 11.900
RECHNUNGEN = [
    (101, date(2025, 1, 15), 10001, "5950.00"),
    (102, date(2025, 2, 15), 10001, "4760.00"),
    (103, date(2025, 3, 15), 10003, "7140.00"),
    (104, date(2025, 4, 15), 10001, "5950.00"),
    (106, date(2025, 5, 15), 10003, "8330.00"),
    (107, date(2025, 6, 15), 10001, "5950.00"),
    (108, date(2025, 7, 15), 10001, "4165.00"),
    (108, date(2025, 8, 20), 10003, "2380.00"),
    (109, date(2025, 10, 20), 10001, "5950.00"),
    (110, date(2025, 10, 5), 10003, "3570.00"),
    (111, date(2025, 11, 15), 10001, "5950.00"),
    (112, date(2025, 12, 15), 10003, "7140.00"),
    (113, date(2025, 12, 30), 10001, "11900.00"),
]
for nr, tag, debitor, betrag in RECHNUNGEN:
    buche(betrag, "S", debitor, 8400, tag,
          f"Ausgangsrechnung {tag.month:02d}/2025", beleg=f"RE2025-{nr}")

ZAHLUNGEN = [  # Bank an Debitor; 111/112/113 bleiben offen
    (101, date(2025, 1, 25), 10001, "5950.00"),
    (102, date(2025, 2, 25), 10001, "4760.00"),
    (103, date(2025, 3, 25), 10003, "7140.00"),
    (104, date(2025, 4, 25), 10001, "5950.00"),
    (106, date(2025, 5, 25), 10003, "8330.00"),
    (107, date(2025, 6, 25), 10001, "5950.00"),
    (108, date(2025, 7, 25), 10001, "4165.00"),
    (108, date(2025, 9, 15), 10003, "2380.00"),
    (109, date(2025, 11, 15), 10001, "5950.00"),
    (110, date(2025, 11, 15), 10003, "3570.00"),
]
for nr, tag, debitor, betrag in ZAHLUNGEN:
    buche(betrag, "S", 1200, debitor, tag, "Zahlungseingang", beleg=f"RE2025-{nr}")

# OP-01: Zahlung ohne Rechnung -> Debitor im Haben
buche(1500, "S", 1200, 10002, date(2025, 3, 5), "Zahlungseingang ungeklärt")

# --- Wareneingang / Kreditoren ---------------------------------------------
buche(2380, "S", 3400, 70001, date(2025, 1, 10), "Wareneinkauf Januar", beleg="ER-2201")
# ST-01 hoch: identischer Beleg, gleicher Betrag, 3 Tage Abstand
buche(2380, "S", 3400, 70001, date(2025, 3, 5), "Wareneinkauf März", beleg="ER-2288")
buche(2380, "S", 3400, 70001, date(2025, 3, 8), "Wareneinkauf März", beleg="ER-2288")
# KR-01: gleiche Belegnummer, abweichende Betraege
buche(500, "S", 3400, 70001, date(2025, 5, 4), "Teillieferung Frühjahr", beleg="ER-3001")
buche(700, "S", 3400, 70001, date(2025, 5, 10), "Nachlieferung Frühjahr", beleg="ER-3001")
buche(2380, "S", 70001, 1200, date(2025, 2, 15), "Zahlung Delta", beleg="ER-2201")
buche(2380, "S", 70001, 1200, date(2025, 3, 20), "Zahlung Delta", beleg="ER-2288")
buche(2380, "S", 70001, 1200, date(2025, 4, 20), "Zahlung Delta")
# OP-02: Kreditor im Soll
buche(800, "S", 70002, 1200, date(2025, 6, 15), "Doppelzahlung Epsilon?")
# OP-04: Direktverrechnung Debitor/Kreditor
buche(500, "S", 70001, 10001, date(2025, 4, 10), "Verrechnung Gutschrift")
# FR-02: Einmal-Kreditor mit hohem Volumen
buche(14280, "S", 4900, 70009, date(2025, 11, 5), "Projektberatung Sonderprojekt",
      bu="9", beleg="ER-5001")
buche(14280, "S", 70009, 1200, date(2025, 12, 5), "Zahlung Projektberatung", beleg="ER-5001")

# --- Dauerbuchungen ---------------------------------------------------------
for m in range(1, 13):
    buche(6500, "S", 4120, 1200, date(2025, m, 28), f"Gehälter {m:02d}/2025")   # PP-03
    buche(2000, "S", 4210, 1200, date(2025, m, 1), f"Miete Büro {m:02d}/2025")
    buche("178.50", "S", 4530, 1200, date(2025, m, 5), "Kfz-Leasing",
          bu="9", beleg=f"LEAS-{m:02d}")                                        # PP-01
# Doppelte Miete Juli + Generalumkehr (Parser-Test BU 20)
buche(2000, "S", 4210, 1200, date(2025, 7, 5), "Miete doppelt erfasst", beleg="M-07b")
buche(2000, "S", 4210, 1200, date(2025, 7, 6), "Storno Miete doppelt", bu="20", beleg="M-07b")

# Telefon: 12 Monatsbeträge + Ausreißer ohne Beleg (ST-02, US-10) + US-05
TELEFON = ["83.30", "85.68", "84.49", "86.87", "83.30", "88.06",
           "84.49", "85.68", "83.30", "86.87", "84.49", "85.68"]
for m, betrag in enumerate(TELEFON, start=1):
    buche(betrag, "S", 4920, 1200, date(2025, m, 12), f"Telefon/Internet {m:02d}",
          bu="9", beleg=f"TEL-{m:02d}")
buche("4522.00", "S", 4920, 1200, date(2025, 12, 15), "Nachzahlung Telekom Streitfall", bu="9")
buche("84.49", "S", 4920, 1200, date(2025, 6, 8), "Telefon Juni ohne Schlüssel", beleg="TEL-06b")

# Werbekosten: 250 EUR monatlich + Dezember-Kampagne (GV-01) + BU-8-Abweichler (US-09)
for m in range(1, 12):
    buche(250, "S", 4600, 70003, date(2025, m, 20), "Anzeigenschaltung Regionalblatt",
          bu="9", beleg=f"WK-{m:02d}")
buche(250, "S", 4600, 70003, date(2025, 10, 24), "Anzeige Sonderformat",
      bu="8", beleg="WK-10b")
for i, tag in enumerate((5, 13, 21)):
    buche(1300, "S", 4600, 70003, date(2025, 12, tag), "Kampagne Winter",
          bu="9", beleg=f"WK-12{'abc'[i]}")

# --- Kasse -------------------------------------------------------------------
# Woechentliche Bareinnahmen (freitags) an 8404 (Automatik 19 %).
# Luecke 16.08.-09.10. (SB-08) | 11.07.->So 13.07. + 02.05.->Feiertag 01.05. (ST-04)
tag = date(2025, 1, 3)
i = 0
while tag <= date(2025, 12, 31):
    if not (date(2025, 8, 16) <= tag <= date(2025, 10, 9)):
        buchungstag = tag
        if tag == date(2025, 7, 11):
            buchungstag = date(2025, 7, 13)
        if tag == date(2025, 5, 2):
            buchungstag = date(2025, 5, 1)
        betrag = D(380 + (i * 37) % 140) + D("0.50")
        buche(betrag, "S", 1000, 8404, buchungstag, "Bareinnahmen Ladengeschäft")
        i += 1
    tag += timedelta(days=7)
# Bareinzahlungen auf Bank (nicht im Aug/Sep - keine Einnahmen)
for m in range(1, 13):
    if m in (8, 9):
        continue
    buche(1300, "S", 1200, 1000, date(2025, m, 28), "Bareinzahlung Bank", beleg=f"EZ-{m:02d}")
# Kleine Barausgaben Buerobedarf
for m, betrag in ((1, 60), (2, 55), (4, 70), (5, 45), (6, 80), (7, 65), (11, 50), (12, 75)):
    buche(betrag, "S", 4930, 1000, date(2025, m, 10), "Büromaterial bar", beleg=f"BAR-{m:02d}")
# SB-01/SB-09: grosse Barausgabe -> Kasse negativ ab 15.03., Heilung 20.03.
buche(4500, "S", 4930, 1000, date(2025, 3, 15), "Messestand Sonderaktion bar", beleg="BAR-M1")
buche(1000, "S", 1000, 1200, date(2025, 3, 20), "Bareinzahlung vom Geschäftskonto")
# US-04: Bewirtung bar, kein nicht abziehbarer Anteil gebucht
buche(476, "S", 4650, 1000, date(2025, 5, 11), "Bewirtung Mandanten", bu="9", beleg="BW-01")
# GV-02: Gegenlauf auf haben-dominantem Erlöskonto
buche(520, "S", 8404, 1000, date(2025, 11, 15), "Rückerstattung Barverkauf")
# GV-03: einmalige Kontierung Lohn an Kasse
buche(800, "S", 4120, 1000, date(2025, 6, 25), "Aushilfslohn bar", beleg="LO-06")
# US-08: VSt-Schlüssel auf USt-Automatikkonto
buche(214, "S", 1000, 8400, date(2025, 12, 5), "Barverkauf Sonderposten",
      bu="8", beleg="BAR-S1")
# SB-03: Geldtransit bleibt offen
buche(500, "S", 1360, 1000, date(2025, 12, 30), "Einzahlung unterwegs")
# DQ-01: ungueltiges Belegdatum 30.02.
buche(50, "S", 4980, 1000, "3002", "Kleinmaterial", beleg="BAR-X")

# --- Anlagevermoegen / AfA ---------------------------------------------------
buche(3000, "S", 4832, 320, date(2025, 12, 31), "AfA Pkw")
buche(1600, "S", 4830, 65, date(2025, 12, 31), "AfA Grundstück")          # AF-03
buche(476, "S", 400, 1200, date(2025, 5, 4), "Schreibtisch", bu="9", beleg="AR-401")   # AF-04 Hinweis
buche(1190, "S", 480, 70001, date(2025, 6, 10), "Werkbank", bu="9", beleg="ER-2410")   # AF-04 mittel
buche("892.50", "S", 480, 70001, date(2025, 11, 5), "Regalsystem Teil 1", bu="9", beleg="ER-2501")  # ST-07
buche("856.80", "S", 480, 70001, date(2025, 11, 12), "Regalsystem Teil 2", bu="9", beleg="ER-2502")
buche(28560, "S", 4800, 70001, date(2025, 9, 15), "Generalüberholung CNC-Maschine",
      bu="9", beleg="ER-2450")  # AF-05

# --- Weitere Fehlerbilder ----------------------------------------------------
buche(2261, "S", 4930, 1200, date(2025, 6, 20), "Armbanduhr Jubiläum Geschäftsführer", bu="9", beleg="AR-777")
buche(1800, "S", 4260, 1200, date(2025, 7, 8), "Dachreparatur EFH Musterweg 3", beleg="HW-19")
buche(5000, "S", 4900, 1200, date(2025, 3, 11), "Beratung pauschal lt. Absprache")      # ST-03
buche(1190, "S", 4360, 1200, date(2025, 4, 1), "Betriebshaftpflicht", bu="9", beleg="VS-01")  # US-01
buche(250, "S", 1576, 1200, date(2025, 7, 15), "VSt-Korrektur manuell")                # US-02
buche(1160, "S", 10001, 8500, date(2025, 9, 5), "Sonderposten Provision", bu="5", beleg="RE2025-S01")  # US-03 (16 %)
buche(119, "S", 4980, 1200, date(2025, 6, 2), "Sonstiger Betriebsbedarf", bu="6", beleg="ER-9")        # US-03 unbekannt
buche(200, "S", 8100, 10001, date(2025, 11, 30), "Korrektur Erlöse")                   # SB-02
buche(750, "S", 1590, 1200, date(2025, 9, 11), "Durchlaufender Posten Gericht")        # SB-04
buche("89.25", "S", 4630, 1200, date(2025, 12, 10), "Geschenk Kunde Weihnachten",
      bu="9", beleg="GS-01")                                                           # ET-01
buche(238, "S", 4900, 1200, date(2025, 8, 8), "Bußgeld Falschparken Firmenwagen", beleg="BG-01")  # ET-02
buche(7000, "S", 1530, 1200, date(2025, 1, 4), "Darlehen an Gesellschafter", beleg="GD-01")       # GS-01
buche(1000, "S", 800, 1200, date(2025, 6, 15), "Kapitalübertrag lt. Absprache", beleg="EK-01")    # BL-04
buche(0, "S", 4980, 1200, date(2025, 1, 6), "Nullbuchung Systemtest", beleg="SYS-0")              # DV-01
# KSt-Vorauszahlungen (KapG-Indiz für DQ-02)
for quartal, monat in enumerate((3, 6, 9, 12), start=1):
    buche(1500, "S", 2200, 1200, date(2025, monat, 10),
          f"KSt-Vorauszahlung Q{quartal}", beleg=f"FA-KSt-{quartal}")
# PP-02: Privatentnahmen nur zum Jahresende
buche(2500, "S", 1800, 1200, date(2025, 12, 29), "Privatentnahme")
buche(1800, "S", 1800, 1200, date(2025, 12, 30), "Privatentnahme")
buche(2200, "S", 1800, 1200, date(2025, 12, 31), "Privatentnahme")


# --- Kassenverlauf kontrollieren ---------------------------------------------
def kassenverlauf() -> tuple[Decimal, Decimal]:
    bewegungen = []
    for umsatz, sh, konto, gegen, bu, datum, _beleg, _text in BUCHUNGEN:
        if not isinstance(datum, date):
            continue
        s = umsatz if sh == "S" else -umsatz
        if bu.startswith("2") and len(bu) >= 2:
            s = -s
        if konto == 1000:
            bewegungen.append((datum, s))
        if gegen == 1000:
            bewegungen.append((datum, -s))
    bewegungen.sort(key=lambda e: e[0])
    kum, minimum = D(0), D(0)
    for _d, w in bewegungen:
        kum += w
        minimum = min(minimum, kum)
    return minimum, kum


# --- SuSa berechnen (wahre FIBU-Sicht: netto + Steuerkonten) ------------------
SCHLUESSEL = {"9": ("VSt", 19), "8": ("VSt", 7), "7": ("VSt", 16),
              "5": ("USt", 16), "3": ("USt", 19), "2": ("USt", 7)}
AUTOMATIK = [(8400, 8409, "USt", 19), (8300, 8309, "USt", 7),
             (3400, 3409, "VSt", 19), (3300, 3309, "VSt", 7)]


def ist_sachaufwand_seite(konto: int) -> bool:
    return (2000 <= konto <= 4999 or 8000 <= konto <= 8999
            or 10 <= konto <= 799)


def susa_berechnen() -> dict[int, Decimal]:
    salden: dict[int, Decimal] = defaultdict(D)
    for umsatz, sh, konto, gegen, bu, _datum, _beleg, _text in BUCHUNGEN:
        s = umsatz if sh == "S" else -umsatz
        if bu.startswith("2") and len(bu) >= 2:
            s = -s
        salden[konto] += s
        salden[gegen] -= s
        art_satz, seite = None, None
        if bu and not bu.startswith("2"):
            art_satz = SCHLUESSEL.get(bu[-1])
        elif not bu:
            for von, bis, art, satz in AUTOMATIK:
                if von <= konto <= bis:
                    art_satz, seite = (art, satz), konto
                    break
                if von <= gegen <= bis:
                    art_satz, seite = (art, satz), gegen
                    break
        if not art_satz:
            continue
        if seite is None:
            seite = konto if ist_sachaufwand_seite(konto) else gegen
        wert = s if seite == konto else -s
        anteil = (wert * art_satz[1] / (100 + art_satz[1])).quantize(D("0.01"))
        salden[seite] -= anteil
        salden[1576 if art_satz[0] == "VSt" else 1776] += anteil
    return salden


# --- Dateien schreiben --------------------------------------------------------
def _feld_datum(datum) -> str:
    if isinstance(datum, date):
        return f"{datum.day}{datum.month:02d}"
    return str(datum)


def schreibe_stapel() -> Path:
    kopf1 = ('"EXTF";700;21;"Buchungsstapel";12;20260812090000000;;"RE";"";"";'
             '12345;67890;20250101;4;20250101;20251231;"Demo 2025";"MF";1;0;0;'
             '"EUR";;"";;;"";;"";;""')
    kopf2 = ('"Umsatz (ohne Soll/Haben-Kz)";"Soll/Haben-Kennzeichen";'
             '"WKZ Umsatz";"Kurs";"Basis-Umsatz";"WKZ Basis-Umsatz";"Konto";'
             '"Gegenkonto (ohne BU-Schlüssel)";"BU-Schlüssel";"Belegdatum";'
             '"Belegfeld 1";"Belegfeld 2";"Skonto";"Buchungstext";'
             '"KOST1-Kostenstelle";"KOST2-Kostenstelle"')
    zeilen = [kopf1, kopf2]
    for umsatz, sh, konto, gegen, bu, datum, beleg, text in BUCHUNGEN:
        betrag = f"{umsatz:.2f}".replace(".", ",")
        zeilen.append(
            f'{betrag};"{sh}";"EUR";;;;{konto};{gegen};"{bu}";'
            f'{_feld_datum(datum)};"{beleg}";"";;"{text}";"";""')
    pfad = ZIEL / "EXTF_Buchungsstapel_2025_Demo.csv"
    pfad.write_bytes(("\r\n".join(zeilen) + "\r\n").encode("cp1252"))
    return pfad


KONTONAMEN = {
    65: "Unbebaute Grundstücke", 320: "Pkw", 400: "Betriebsausstattung",
    480: "Geringwertige Wirtschaftsgüter", 800: "Gezeichnetes Kapital",
    840: "Kapitalrücklage", 860: "Gewinnvortrag vor Verwendung",
    970: "Sonstige Rückstellungen", 980: "Aktive Rechnungsabgrenzung",
    1000: "Kasse", 1200: "Bank", 1360: "Geldtransit",
    1530: "Forderungen gegen Gesellschafter",
    1576: "Abziehbare Vorsteuer 19 %", 1590: "Durchlaufende Posten",
    1776: "Umsatzsteuer 19 %", 1800: "Privatentnahmen",
    2200: "Körperschaftsteuer", 3400: "Wareneingang 19 % VSt",
    4120: "Gehälter",
    4210: "Miete Geschäftsräume", 4260: "Instandhaltung betriebl. Räume",
    4320: "Gewerbesteuer", 4360: "Versicherungen",
    4530: "Laufende Kfz-Betriebskosten", 4630: "Geschenke abzugsfähig",
    4650: "Bewirtungskosten", 4800: "Reparatur u. Instandh. Anlagen",
    4830: "Abschreibungen auf Sachanlagen", 4832: "AfA Kfz",
    4900: "Sonstige betriebliche Aufwendungen", 4920: "Telefon",
    4930: "Bürobedarf", 4980: "Betriebsbedarf",
    8100: "Steuerfreie Umsätze § 4 UStG", 8400: "Erlöse 19 % USt",
    8404: "Erlöse Ladengeschäft 19 % USt", 8500: "Provisionserlöse",
    9000: "Saldenvorträge Sachkonten",
    10001: "Kunde Alpha GmbH", 10002: "Kunde Beta AG",
    10003: "Kunde Gamma KG", 10004: "Kunde Alpha GmbH",
    10005: "Kunde Omega (inaktiv)",
    70001: "Lieferant Delta GmbH", 70002: "Lieferant Epsilon e.K.",
    70003: "Werbeagentur Zeta",
}
# Bewusst OHNE Beschriftung (DV-03): 4600, 70009
# SD-01: 10004 traegt denselben Namen wie 10001


def schreibe_kontenbeschriftungen() -> Path:
    kopf1 = ('"EXTF";700;20;"Kontenbeschriftungen";2;20260812090000000;;"RE";'
             '"";"";12345;67890;20250101;4;;;"Kontenbeschriftungen"')
    zeilen = [kopf1, '"Konto";"Kontenbeschriftung"']
    for konto, name in sorted(KONTONAMEN.items()):
        zeilen.append(f'{konto};"{name}"')
    pfad = ZIEL / "EXTF_Kontenbeschriftungen_Demo.csv"
    pfad.write_bytes(("\r\n".join(zeilen) + "\r\n").encode("cp1252"))
    return pfad


def schreibe_susa() -> Path:
    salden = susa_berechnen()
    salden[1000] += D(150)   # SB-05: Kassendifferenz zur SuSa
    salden[1576] -= D(100)   # US-07: VSt-Verprobungsdifferenz
    zeilen = ["Konto;Saldo"]
    for konto in sorted(salden):
        if 9000 <= konto <= 9099:
            continue
        zeilen.append(f'{konto};{f"{salden[konto]:.2f}".replace(".", ",")}')
    pfad = ZIEL / "SuSa_2025_Demo.csv"
    pfad.write_bytes(("\r\n".join(zeilen) + "\r\n").encode("cp1252"))
    return pfad


# Schlussbestaende des Vorjahres (Bilanz auf Kontenebene). Gewollte Faelle:
# 1200 Bank: VJ 44.000 vs. EB 45.000 (VJ-01 Differenz) | 1590: VJ-Bestand
# ohne EB-Uebernahme (VJ-01) | 800 EK: Differenz 1.000 (Hinweis, kapitalnah,
# konsistent zur SB-06-Story "EB-Uebernahme unvollstaendig")
VJ_BESTAND = {
    1000: "2000.00", 1200: "44000.00", 320: "18000.00", 65: "80000.00",
    10001: "3570.00", 70001: "-5950.00", 980: "1200.00", 970: "-5000.00",
    800: "-25000.00", 840: "-30000.00", 860: "-83520.00", 1590: "400.00",
}


def schreibe_susa_vorjahr() -> Path:
    """VJ-SuSa = Bilanz + GuV des Vorjahres auf Kontenebene.
    GuV-Faelle: 4600 stark gestiegen (VJ-02) | 4800 erstmalig (kein
    VJ-Wert) | 4640 im VJ bebucht, jetzt ohne Saldo (VJ-02)."""
    vj: dict[int, Decimal] = {k: D(v) for k, v in VJ_BESTAND.items()}
    for konto, saldo in susa_berechnen().items():
        if 2000 <= konto <= 4999 or 8000 <= konto <= 8999:
            vj.setdefault(konto, saldo)  # GuV im VJ ~ unveraendert
    vj[4600] = D("1200.00")
    vj[4640] = D("3000.00")
    vj.pop(4800, None)
    zeilen = ["Konto;Saldo"]
    for konto in sorted(vj):
        zeilen.append(f'{konto};{f"{vj[konto]:.2f}".replace(".", ",")}')
    pfad = ZIEL / "SuSa_2024_Demo.csv"
    pfad.write_bytes(("\r\n".join(zeilen) + "\r\n").encode("cp1252"))
    return pfad


def schreibe_opos() -> Path:
    zeilen = ["Konto;Belegnr;Belegdatum;Faelligkeit;Betrag offen",
              "10001;RE2024-098;15.11.2024;15.12.2024;3570,00",
              "10001;RE2025-111;15.11.2025;15.12.2025;5950,00",
              "10001;RE2025-113;30.12.2025;29.01.2026;11900,00",
              "10001;GS-2024-05;01.09.2024;01.10.2024;-250,00",
              "10003;RE2025-112;15.12.2025;14.01.2026;7140,00",
              "10005;RE2023-045;10.05.2023;10.06.2023;12,40",
              "70002;ER-2024-77;01.10.2024;31.10.2024;5950,00"]
    pfad = ZIEL / "OPOS_2025_Demo.csv"
    pfad.write_bytes(("\r\n".join(zeilen) + "\r\n").encode("cp1252"))
    return pfad


if __name__ == "__main__":
    minimum, ende = kassenverlauf()
    print(f"{len(BUCHUNGEN)} Buchungszeilen | Kasse: Minimum {minimum}, "
          f"Endstand {ende} (erwartet: Minimum < 0, Endstand >= 0)")
    for pfad in (schreibe_stapel(), schreibe_kontenbeschriftungen(),
                 schreibe_susa(), schreibe_susa_vorjahr(), schreibe_opos()):
        print(f"geschrieben: {pfad.name}")
