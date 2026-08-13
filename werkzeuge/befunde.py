"""Befund-Modell, Prüfkatalog und Prüfkontext (aggregierte Sichten)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from datev_parser import Buchung, OposPosten, StapelInfo
from kontenplan import Kontenplan

RANG = {"hoch": 0, "mittel": 1, "hinweis": 2}

# Prüfebenen (Strukturierung nach dem Prüfkatalog):
# 1 = technische Integrität, 2 = Regelprüfung, 3 = Plausibilität, 4 = Anomalie
EBENEN = {1: "Integrität", 2: "Regel", 3: "Plausibilität", 4: "Anomalie"}

# Vollständiger Katalog (auch fuer 0-Treffer-Ausweis im Bericht):
# (Check-ID, Name, Bereich, Ebene 1-4, Klasse R/P/A [ggf. /X = Zusatzdaten])
KATALOG: list[tuple[str, str, str, int, str]] = [
    ("DV-01", "Nullbeträge und Konto = Gegenkonto", "Datenintegrität", 1, "R"),
    ("DV-02", "EB-Buchungen auf GuV-Konten", "Datenintegrität", 1, "R"),
    ("DV-03", "Bebuchte Konten ohne Kontenbeschriftung", "Datenintegrität", 1, "R/X"),
    ("DQ-01", "Datenqualität Import", "Datenintegrität", 1, "R"),
    ("DQ-02", "Rechtsform-Konsistenz (Name/Angabe/Kontenbild)", "Datenintegrität", 1, "R"),
    ("ST-05", "Fehlende Belegnummern/Buchungstexte", "Datenintegrität", 1, "P"),
    ("ST-06", "Belegdatum außerhalb des Zeitraums", "Datenintegrität", 1, "R"),
    ("SB-01", "Negative Kasse", "Salden", 2, "R"),
    ("SB-02", "Unplausibles Saldenvorzeichen", "Salden", 3, "P"),
    ("SB-03", "Geldtransit nicht ausgeglichen", "Salden", 2, "R"),
    ("SB-04", "Interims-/Verrechnungskonten nicht ausgeglichen", "Salden", 2, "R"),
    ("SB-05", "Abweichung zur Summen- und Saldenliste", "Salden", 1, "R/X"),
    ("SB-06", "Saldenvorträge saldieren nicht auf null", "Salden", 1, "R"),
    ("SB-07", "Ungewöhnlich hoher Kassenbestand", "Salden", 3, "P"),
    ("SB-08", "Lücken in der Kassenführung", "Salden", 3, "P"),
    ("SB-09", "Ausreißer-Einzelbewegungen Kasse", "Salden", 3, "P"),
    ("SB-10", "Glatte Barbewegungen Kasse/Privat", "Salden", 4, "A"),
    ("AF-01", "Anlagenzugänge ohne Abschreibung", "AfA", 2, "R"),
    ("AF-02", "Abschreibung ohne Anlagevermögen", "AfA", 3, "P"),
    ("AF-03", "AfA auf nicht abnutzbares Anlagevermögen", "AfA", 2, "R"),
    ("AF-04", "GWG-Grenzen", "AfA", 2, "R"),
    ("AF-05", "Aktivierungspflicht-Kandidaten (Instandhaltung)", "AfA", 3, "P"),
    ("US-01", "Vorsteuerschlüssel auf untypischem Konto", "USt/VSt", 2, "R"),
    ("US-02", "Direktbuchungen auf Steuerkonten", "USt/VSt", 3, "P"),
    ("US-03", "Ungültige oder historische Steuerschlüssel", "USt/VSt", 2, "R"),
    ("US-04", "Bewirtung ohne nicht abziehbaren Anteil", "USt/VSt", 2, "R"),
    ("US-05", "Steuerschlüssel-Abweichler je Sachkonto", "USt/VSt", 4, "A"),
    ("US-06", "USt-Verprobung (Erlöse)", "USt/VSt", 2, "R/X"),
    ("US-07", "VSt-Verprobung (Aufwand)", "USt/VSt", 2, "R/X"),
    ("US-08", "Steuerschlüssel weicht von Automatikkonto ab", "USt/VSt", 2, "R"),
    ("US-09", "Steuerschlüssel-Wechsel je Geschäftspartner", "USt/VSt", 4, "A"),
    ("US-10", "Vorsteuerbuchungen ohne Belegnummer", "USt/VSt", 3, "P"),
    ("RE-01", "Lücken in der Rechnungsnummernfolge", "Ausgangsrechnungen", 2, "R"),
    ("RE-02", "Doppelt vergebene Rechnungsnummern", "Ausgangsrechnungen", 2, "R"),
    ("RE-03", "Rechnungsdatum entgegen Nummernfolge", "Ausgangsrechnungen", 3, "P"),
    ("OP-01", "Debitoren mit Habensaldo", "OPOS/Kreditoren", 2, "R"),
    ("OP-02", "Kreditoren mit Sollsaldo", "OPOS/Kreditoren", 2, "R"),
    ("OP-03", "Überfällige offene Posten", "OPOS/Kreditoren", 3, "P/X"),
    ("OP-04", "Direktverrechnung Debitor/Kreditor", "OPOS/Kreditoren", 2, "R"),
    ("OP-05", "OPOS-Summen weichen vom Kontensaldo ab", "OPOS/Kreditoren", 1, "R/X"),
    ("OP-06", "Alte Kleinstposten und alte Gutschriften", "OPOS/Kreditoren", 3, "P/X"),
    ("OP-07", "Konzentration auf einzelne Debitoren", "OPOS/Kreditoren", 3, "P"),
    ("KR-01", "Gleiche Rechnungsnummer beim selben Kreditor", "OPOS/Kreditoren", 2, "R"),
    ("BL-01", "Rechnungsabgrenzung ohne Bewegung/Auflösung", "Bilanz (sonstige)", 3, "P"),
    ("BL-02", "Rückstellungen ohne jede Bewegung", "Bilanz (sonstige)", 3, "P"),
    ("BL-03", "Darlehen ohne Zinsaufwand", "Bilanz (sonstige)", 3, "P"),
    ("BL-04", "Direktbuchungen auf Eigenkapitalkonten", "Bilanz (sonstige)", 3, "P"),
    ("BL-05", "Latente Steuern (Ansatz und Steuersatz-Staffel)", "Bilanz (sonstige)", 3, "P/X"),
    ("VJ-01", "EB-Werte gegen Schlussbilanz des Vorjahres", "Vorjahresvergleich", 1, "R/X"),
    ("VJ-02", "GuV-Konten gegen Vorjahr", "Vorjahresvergleich", 3, "P/X"),
    ("GV-01", "Ungewöhnliche Monatsspitzen je Konto", "GuV-Plausibilität", 4, "A"),
    ("GV-02", "Gegenläufige Buchung auf richtungsstabilem Konto", "GuV-Plausibilität", 4, "A"),
    ("GV-03", "Seltene Konten-Gegenkonto-Kombination", "GuV-Plausibilität", 4, "A"),
    ("ET-01", "Geschenke über der Abzugsgrenze", "Ertragsteuer", 2, "R"),
    ("ET-02", "Steuersensible Buchungstexte auf untypischen Konten", "Ertragsteuer", 2, "R"),
    ("CO-01", "Wesentliche Buchungen unmittelbar am Periodenende", "Cut-off", 3, "P"),
    ("PP-01", "Kfz-Kosten ohne erkennbare Privatnutzung", "Personal/Privat", 3, "P"),
    ("PP-02", "Privatbuchungen nur zum Jahresende", "Personal/Privat", 3, "P"),
    ("PP-03", "Lohnaufwand ohne LSt-/SV-Verbindlichkeiten", "Personal/Privat", 2, "R"),
    ("PP-04", "Privatkonten bei Kapitalgesellschaft bebucht", "Personal/Privat", 2, "R"),
    ("GS-01", "Bewegungen auf Gesellschafterkonten", "Gesellschafter", 3, "P"),
    ("ST-01", "Doppelbuchungs-Verdacht", "Statistik", 3, "P"),
    ("ST-02", "Betragsausreißer je Konto", "Statistik", 4, "A"),
    ("ST-03", "Auffällig runde Beträge", "Statistik", 4, "A"),
    ("ST-04", "Kassenbuchungen an Sonn- und Feiertagen", "Statistik", 4, "A"),
    ("ST-07", "Schwellen-Splitting (GWG-Grenze)", "Statistik", 4, "A"),
    ("ST-08", "Benford-Analyse (erste Ziffer)", "Statistik", 4, "A"),
    ("FR-01", "Stornoquote und Storno-Wiederholungen", "Fraud-Indikatoren", 4, "A"),
    ("FR-02", "Einmal-Kreditoren mit wesentlichem Volumen", "Fraud-Indikatoren", 4, "A"),
    ("FR-03", "Beträge knapp unter Freigabegrenzen", "Fraud-Indikatoren", 3, "P/X"),
    ("FR-04", "Häufung glatter Centbeträge (Endziffern)", "Fraud-Indikatoren", 4, "A"),
    ("SD-01", "Personenkonten mit identischer Bezeichnung", "Stammdaten", 3, "P/X"),
]
# Datenbasis je Check als Quellen-Fallback, wenn keine Einzelbuchung
# (Datei:Zeile) benennbar ist - keine leeren Quellenangaben im Bericht.
QUELLEN_BASIS = {
    "SB-05": "SuSa ↔ Buchungsstapel",
    "US-06": "SuSa ↔ Buchungsstapel (rechnerische USt)",
    "US-07": "SuSa ↔ Buchungsstapel (rechnerische VSt)",
    "OP-03": "OPOS-Liste",
    "OP-06": "OPOS-Liste",
    "OP-05": "OPOS-Liste ↔ Buchungsstapel",
    "VJ-01": "Vorjahres-SuSa ↔ EB-Buchungen (Stapel)",
    "VJ-02": "Vorjahres-SuSa ↔ Buchungsstapel",
    "BL-02": "Buchungsstapel (bei VJ-Vergleich: ↔ Vorjahres-SuSa)",
    "DV-03": "Kontenbeschriftungen (Kat. 20) ↔ Buchungsstapel",
    "SD-01": "Kontenbeschriftungen (Kat. 20)",
    "DQ-01": "Import-Protokoll des Parsers",
    "DQ-02": "Mandantenname ↔ Rechtsform-Angabe ↔ Kontenbild",
}
KATALOG_NAMEN = {cid: name for cid, name, _b, _e, _k in KATALOG}
KATALOG_BEREICHE = {cid: bereich for cid, _n, bereich, _e, _k in KATALOG}
KATALOG_EBENE = {cid: ebene for cid, _n, _b, ebene, _k in KATALOG}
KATALOG_KLASSE = {cid: klasse for cid, _n, _b, _e, klasse in KATALOG}


def eur(x: Decimal | float | int) -> str:
    s = f"{float(x):,.2f}"
    return s.replace(",", " ").replace(".", ",").replace(" ", ".")


@dataclass
class Befund:
    check_id: str
    schwere: str
    text: str
    empfehlung: str = ""
    konto: int | None = None
    gegenkonto: int | None = None
    datum: date | None = None
    betrag: Decimal | None = None
    beleg: str = ""
    buchungstext: str = ""
    quelle: str = ""
    llm_kandidat: bool = False

    @property
    def check_name(self) -> str:
        return KATALOG_NAMEN.get(self.check_id, self.check_id)

    @property
    def bereich(self) -> str:
        return KATALOG_BEREICHE.get(self.check_id, "Sonstiges")

    @property
    def ebene(self) -> int:
        return KATALOG_EBENE.get(self.check_id, 3)

    @property
    def klasse(self) -> str:
        return KATALOG_KLASSE.get(self.check_id, "P")

    def as_dict(self) -> dict:
        return {
            "check_id": self.check_id, "check": self.check_name,
            "bereich": self.bereich, "ebene": self.ebene,
            "klasse": self.klasse, "schwere": self.schwere,
            "konto": self.konto, "gegenkonto": self.gegenkonto,
            "datum": self.datum.isoformat() if self.datum else None,
            "betrag": float(self.betrag) if self.betrag is not None else None,
            "beleg": self.beleg, "buchungstext": self.buchungstext,
            "text": self.text, "empfehlung": self.empfehlung,
            "quelle": self.quelle, "llm_kandidat": self.llm_kandidat,
        }


class Kontext:
    """Aggregierte Sichten auf den Buchungsbestand fuer alle Checks."""

    def __init__(self, buchungen: list[Buchung], plan: Kontenplan,
                 param: dict, infos: list[StapelInfo],
                 namen: dict[int, str] | None = None,
                 susa: dict[int, Decimal] | None = None,
                 opos: list[OposPosten] | None = None,
                 warnungen: list[str] | None = None,
                 susa_vj: dict[int, Decimal] | None = None,
                 mandant_name: str = ""):
        self.buchungen = buchungen
        self.plan = plan
        self.param = param
        self.infos = infos
        self.namen = namen or {}
        self.susa = susa
        self.opos = opos
        self.susa_vj = susa_vj
        self.mandant_name = mandant_name
        self.ust_rechnerisch: Decimal | None = None
        self.vst_rechnerisch: Decimal | None = None
        self.warnungen = warnungen or []
        self.geskippt: dict[str, str] = {}
        self.kennzahlen: dict[str, str] = {}
        self.bagatelle = Decimal(str(param["bagatelle_eur"]))
        von = [i.datum_von for i in infos if i.datum_von]
        bis = [i.datum_bis for i in infos if i.datum_bis]
        self.datum_von: date | None = min(von) if von else None
        self.datum_bis: date | None = max(bis) if bis else None
        self._aggregiere()

    def ist_eb(self, b: Buchung) -> bool:
        return (self.plan.in_gruppe(b.konto, "saldovortrag")
                or self.plan.in_gruppe(b.gegenkonto, "saldovortrag"))

    def _aggregiere(self) -> None:
        self.saldo: dict[int, Decimal] = defaultdict(Decimal)
        self.saldo_netto: dict[int, Decimal] = defaultdict(Decimal)
        self.soll: dict[int, Decimal] = defaultdict(Decimal)
        self.haben: dict[int, Decimal] = defaultdict(Decimal)
        self.anzahl: dict[int, int] = defaultdict(int)
        self.bewegungen: dict[int, list] = defaultdict(list)
        self.eb_salden: dict[int, Decimal] = defaultdict(Decimal)
        self.eb_vorhanden = False
        for b in self.buchungen:
            s = b.umsatz if b.sh == "S" else -b.umsatz
            if b.storno:
                s = -s
            if self.ist_eb(b):
                if not self.plan.in_gruppe(b.konto, "saldovortrag"):
                    self.eb_salden[b.konto] += s
                if not self.plan.in_gruppe(b.gegenkonto, "saldovortrag"):
                    self.eb_salden[b.gegenkonto] += -s
            st = self.plan.steuer(b)
            for seite, konto, wert in (("konto", b.konto, s),
                                       ("gegenkonto", b.gegenkonto, -s)):
                self.saldo[konto] += wert
                netto = wert
                if st and st[2] == seite and st[1]:
                    netto = (wert * 100 / (100 + st[1])).quantize(Decimal("0.01"))
                self.saldo_netto[konto] += netto
                if wert > 0:
                    self.soll[konto] += wert
                else:
                    self.haben[konto] += -wert
                self.anzahl[konto] += 1
                self.bewegungen[konto].append((b.belegdatum, b.zeile, wert, b))
            if self.ist_eb(b):
                self.eb_vorhanden = True
        maxdatum = date.max
        for k in self.bewegungen:
            self.bewegungen[k].sort(key=lambda e: (e[0] or maxdatum, e[1]))

    def konten_in(self, gruppe: str) -> list[int]:
        return sorted(k for k in self.anzahl if self.plan.in_gruppe(k, gruppe))

    def name(self, konto: int) -> str:
        return self.namen.get(konto, "")

    def kontotext(self, konto: int) -> str:
        n = self.name(konto)
        return f"{konto} ({n})" if n else str(konto)

    def skip(self, check_id: str, grund: str) -> None:
        self.geskippt[check_id] = grund
