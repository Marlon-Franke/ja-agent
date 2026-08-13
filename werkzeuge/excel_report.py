"""Excel-Prüfbericht (openpyxl).

Bewusst ohne Formeln: Der Bericht ist ein statischer Befundbericht,
alle Werte sind deterministisch berechnet (keine Recalc-Abhängigkeit).
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from befunde import EBENEN, KATALOG, RANG, Befund, Kontext, eur

FONT = "Arial"
KOPF_FILL = PatternFill("solid", start_color="1F4E79")
REVIEW_FILL = PatternFill("solid", start_color="7030A0")
KOPF_FONT = Font(name=FONT, size=10, bold=True, color="FFFFFF")
STANDARD = Font(name=FONT, size=10)
SCHWERE_STIL = {
    "hoch": (PatternFill("solid", start_color="C00000"), Font(name=FONT, size=10, bold=True, color="FFFFFF")),
    "mittel": (PatternFill("solid", start_color="FFD966"), Font(name=FONT, size=10, color="000000")),
    "hinweis": (PatternFill("solid", start_color="BDD7EE"), Font(name=FONT, size=10, color="000000")),
}
BLATT_NAMEN = {
    "Datenintegrität": "Datenintegritaet",
    "Salden": "Salden",
    "AfA": "AfA",
    "USt/VSt": "USt-VSt",
    "Ausgangsrechnungen": "Rechnungen",
    "OPOS/Kreditoren": "OPOS-Kreditoren",
    "Bilanz (sonstige)": "Bilanz-Sonstige",
    "Vorjahresvergleich": "Vorjahr",
    "GuV-Plausibilität": "GuV-Plausis",
    "Ertragsteuer": "Ertragsteuer",
    "Cut-off": "Cut-off",
    "Personal/Privat": "Personal-Privat",
    "Gesellschafter": "Gesellschafter",
    "Statistik": "Statistik",
    "Fraud-Indikatoren": "Fraud-Indikatoren",
    "Stammdaten": "Stammdaten",
}

BEFUND_SPALTEN = [
    ("Schwere", 9), ("Check", 7), ("Prüfung", 28), ("Ebene", 13),
    ("Klasse", 7), ("Konto", 9), ("Kontobezeichnung", 20),
    ("Gegenkonto", 11), ("Datum", 11), ("Betrag (EUR)", 13), ("Beleg", 12),
    ("Buchungstext", 24), ("Befund", 55), ("Empfehlung", 42), ("Quelle", 17),
    ("KI", 4), ("Review-Status", 13), ("Bearbeiter", 12), ("Kommentar", 26),
]
KANDIDAT_SPALTEN = [
    ("ID", 6), ("Grund", 30), ("Konto", 9), ("Kontobezeichnung", 20),
    ("Gegenkonto", 11), ("Datum", 11), ("Betrag (EUR)", 13), ("BU", 5),
    ("Beleg", 13), ("Buchungstext", 32), ("Quelle", 17),
    ("KI-Urteil", 18), ("KI-Begründung", 52), ("KI-Schwere", 11),
    ("KI-Konfidenz", 12),
]


def _kopfzeile(ws, spalten, review_ab: int | None = None) -> None:
    for i, (name, breite) in enumerate(spalten, start=1):
        zelle = ws.cell(row=1, column=i, value=name)
        zelle.font = KOPF_FONT
        zelle.fill = REVIEW_FILL if review_ab and i >= review_ab else KOPF_FILL
        zelle.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = breite
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(spalten))}1"


def _zelle(ws, row, col, wert, wrap=False, fmt=None):
    z = ws.cell(row=row, column=col, value=wert)
    z.font = STANDARD
    z.alignment = Alignment(vertical="top", wrap_text=wrap)
    if fmt:
        z.number_format = fmt
    return z


def _befundblatt(wb: Workbook, titel: str, befunde: list[Befund], ctx: Kontext) -> None:
    ws = wb.create_sheet(titel[:31])
    _kopfzeile(ws, BEFUND_SPALTEN, review_ab=17)
    zeile = 2
    for f in sorted(befunde, key=lambda f: (RANG[f.schwere], f.check_id)):
        z = _zelle(ws, zeile, 1, f.schwere.upper())
        fill, font = SCHWERE_STIL[f.schwere]
        z.fill, z.font = fill, font
        z.alignment = Alignment(vertical="top", horizontal="center")
        _zelle(ws, zeile, 2, f.check_id)
        _zelle(ws, zeile, 3, f.check_name, wrap=True)
        _zelle(ws, zeile, 4, f"{f.ebene} {EBENEN[f.ebene]}")
        _zelle(ws, zeile, 5, f.klasse)
        _zelle(ws, zeile, 6, f.konto)
        _zelle(ws, zeile, 7, ctx.name(f.konto) if f.konto else "", wrap=True)
        _zelle(ws, zeile, 8, f.gegenkonto)
        _zelle(ws, zeile, 9, f.datum, fmt="DD.MM.YYYY")
        _zelle(ws, zeile, 10, float(f.betrag) if f.betrag is not None else None,
               fmt="#,##0.00")
        _zelle(ws, zeile, 11, f.beleg)
        _zelle(ws, zeile, 12, f.buchungstext, wrap=True)
        _zelle(ws, zeile, 13, f.text, wrap=True)
        _zelle(ws, zeile, 14, f.empfehlung, wrap=True)
        _zelle(ws, zeile, 15, f.quelle)
        _zelle(ws, zeile, 16, "ja" if f.llm_kandidat else "")
        for spalte in (17, 18, 19):
            _zelle(ws, zeile, spalte, "")
        hoehe = max(math.ceil(len(f.text) / 53), math.ceil(len(f.empfehlung) / 40), 1)
        if hoehe > 1:
            ws.row_dimensions[zeile].height = min(hoehe * 13 + 2, 92)
        zeile += 1


def _uebersicht(ws, ctx: Kontext, befunde: list[Befund], meta: dict) -> None:
    ws.title = "Übersicht"
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 46
    for spalte, breite in zip("CDEFGH", (13, 8, 8, 8, 9, 42)):
        ws.column_dimensions[spalte].width = breite
    titel = _zelle(ws, 1, 1, "Jahresabschluss-Prüfbericht (Entwurf – Arbeitshilfe)")
    titel.font = Font(name=FONT, size=15, bold=True, color="1F4E79")
    zeile = 3
    for label, wert in meta.items():
        _zelle(ws, zeile, 1, label).font = Font(name=FONT, size=10, bold=True)
        _zelle(ws, zeile, 2, wert, wrap=True)
        zeile += 1
    zeile += 1
    _zelle(ws, zeile, 1, "Kennzahlen").font = Font(name=FONT, size=12, bold=True)
    zeile += 1
    for label, wert in ctx.kennzahlen.items():
        _zelle(ws, zeile, 1, label).font = Font(name=FONT, size=10, bold=True)
        _zelle(ws, zeile, 2, wert)
        zeile += 1
    zeile += 1
    _zelle(ws, zeile, 1, "Prüfkatalog und Befundlage").font = Font(name=FONT, size=12, bold=True)
    zeile += 1
    _zelle(ws, zeile, 1,
           "Ebenen: 1 = technische Integrität, 2 = Regelprüfung, "
           "3 = Plausibilität, 4 = Anomalie · Klassen: R = regelbasiert, "
           "P = Plausibilität/Schwellenwert, A = Anomalie-Score, "
           "X = benötigt zusätzliche Datenquelle",
           wrap=True).font = Font(name=FONT, size=9, color="595959")
    ws.merge_cells(start_row=zeile, start_column=1, end_row=zeile, end_column=8)
    zeile += 1
    kopf = ("Check", "Prüfung", "Ebene", "Klasse", "hoch", "mittel", "hinweis", "Status")
    for i, name in enumerate(kopf, start=1):
        z = ws.cell(row=zeile, column=i, value=name)
        z.font, z.fill = KOPF_FONT, KOPF_FILL
    zeile += 1
    je_check: dict[str, dict[str, int]] = {}
    for f in befunde:
        je_check.setdefault(f.check_id, {"hoch": 0, "mittel": 0, "hinweis": 0})
        je_check[f.check_id][f.schwere] += 1
    for cid, name, _bereich, ebene, klasse in KATALOG:
        _zelle(ws, zeile, 1, cid)
        _zelle(ws, zeile, 2, name, wrap=True)
        _zelle(ws, zeile, 3, f"{ebene} {EBENEN[ebene]}")
        _zelle(ws, zeile, 4, klasse).alignment = Alignment(horizontal="center")
        zaehler = je_check.get(cid, {"hoch": 0, "mittel": 0, "hinweis": 0})
        for i, schwere in enumerate(("hoch", "mittel", "hinweis"), start=5):
            z = _zelle(ws, zeile, i, zaehler[schwere] or None)
            z.alignment = Alignment(horizontal="center")
            if zaehler[schwere]:
                z.fill, z.font = SCHWERE_STIL[schwere]
        if cid in ctx.geskippt:
            status = f"zusätzliche Prüfung – {ctx.geskippt[cid]}"
        elif sum(zaehler.values()):
            status = "Befunde – siehe Detailblätter"
        else:
            status = "geprüft, ohne Befund"
        _zelle(ws, zeile, 8, status, wrap=True)
        zeile += 1
    zeile += 1
    _zelle(ws, zeile, 1, "KI-Zusammenfassung").font = Font(name=FONT, size=12, bold=True)
    zeile += 1
    ws.merge_cells(start_row=zeile, start_column=1, end_row=zeile + 4, end_column=8)
    platzhalter = _zelle(ws, zeile, 1,
        "– noch nicht erstellt; wird nach der KI-Durchsicht der Kandidaten "
        "ergänzt (werkzeuge/llm_einarbeiten.py) –", wrap=True)
    platzhalter.font = Font(name=FONT, size=10, italic=True, color="808080")
    zeile += 6
    ws.merge_cells(start_row=zeile, start_column=1, end_row=zeile + 3, end_column=8)
    _zelle(ws, zeile, 1,
        "Methodik: Deterministische Prüfung des DATEV-Buchungsstapels in vier "
        "Ebenen (Integrität, Regel, Plausibilität, Anomalie) – Regeln in Code, "
        "kein LLM; KI nur für die als 'KI' markierten Kandidaten. Stapeldaten "
        "enthalten Bruttoumsätze mit BU-Schlüsseln; GuV-Nettowerte und "
        "Steuerbeträge sind daraus rechnerisch abgeleitet. Kontengruppen gem. "
        "werkzeuge/konten_config.json (SKR-Standard, anpassbar). Prüfungen mit "
        "Status 'zusätzliche Prüfung' werden aktiv, sobald die genannte "
        "Datenquelle angeliefert wird. Diese Arbeitshilfe ersetzt keine "
        "fachliche Würdigung.",
        wrap=True).font = Font(name=FONT, size=9, color="595959")


def _kandidatenblatt(wb: Workbook, kandidaten: list[dict], ctx: Kontext) -> None:
    ws = wb.create_sheet("KI-Kandidaten")
    _kopfzeile(ws, KANDIDAT_SPALTEN, review_ab=12)
    for zeile, k in enumerate(kandidaten, start=2):
        _zelle(ws, zeile, 1, k["id"])
        _zelle(ws, zeile, 2, k["grund"], wrap=True)
        _zelle(ws, zeile, 3, k["konto"])
        _zelle(ws, zeile, 4, k["konto_name"], wrap=True)
        _zelle(ws, zeile, 5, k["gegenkonto"])
        datum = date.fromisoformat(k["datum"]) if k["datum"] else None
        _zelle(ws, zeile, 6, datum, fmt="DD.MM.YYYY")
        _zelle(ws, zeile, 7, k["betrag"], fmt="#,##0.00")
        _zelle(ws, zeile, 8, k["bu"])
        _zelle(ws, zeile, 9, k["beleg"])
        _zelle(ws, zeile, 10, k["buchungstext"], wrap=True)
        _zelle(ws, zeile, 11, k["quelle"])


_AGING_STUFEN = [(0, "nicht fällig"), (30, "0–30 Tage"), (60, "31–60 Tage"),
                 (90, "61–90 Tage"), (180, "91–180 Tage"),
                 (365, "181–365 Tage"), (99999, "> 365 Tage")]


def _aging_stufe(tage: int) -> str:
    if tage < 0:
        return "nicht fällig"
    for grenze, label in _AGING_STUFEN[1:]:
        if tage <= grenze:
            return label
    return "> 365 Tage"


def _opos_aging(wb: Workbook, ctx: Kontext) -> None:
    if not ctx.opos or ctx.datum_bis is None:
        return
    ws = wb.create_sheet("OPOS-Alterung")
    labels = [label for _g, label in _AGING_STUFEN]
    spalten = [("Konto", 10), ("Bezeichnung", 26), ("Art", 10)] + \
              [(label, 13) for label in labels] + [("Summe", 13), ("Posten", 8)]
    _kopfzeile(ws, spalten)
    je_konto: dict[int, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    anzahl: dict[int, int] = defaultdict(int)
    for p in ctx.opos:
        datum = p.faellig or p.belegdatum
        stufe = _aging_stufe((ctx.datum_bis - datum).days) if datum else "0–30 Tage"
        je_konto[p.konto][stufe] += p.betrag
        anzahl[p.konto] += 1
    zeile = 2
    for konto in sorted(je_konto):
        art = "Debitor" if ctx.plan.ist_debitor(konto) else (
            "Kreditor" if ctx.plan.ist_kreditor(konto) else "Sachkonto")
        _zelle(ws, zeile, 1, konto)
        _zelle(ws, zeile, 2, ctx.name(konto), wrap=True)
        _zelle(ws, zeile, 3, art)
        gesamt = Decimal(0)
        for i, label in enumerate(labels, start=4):
            wert = je_konto[konto].get(label)
            if wert:
                gesamt += wert
            _zelle(ws, zeile, i, float(wert) if wert else None, fmt="#,##0.00")
        _zelle(ws, zeile, 4 + len(labels), float(gesamt), fmt="#,##0.00")
        _zelle(ws, zeile, 5 + len(labels), anzahl[konto])
        zeile += 1
    _zelle(ws, zeile + 1, 1,
           f"Alter = Stichtag ({ctx.datum_bis:%d.%m.%Y}) minus Fälligkeit "
           "(ersatzweise Belegdatum). Negative Beträge = Gutschriften.",
           wrap=True).font = Font(name=FONT, size=9, italic=True, color="595959")


def _saldenblatt(wb: Workbook, ctx: Kontext) -> None:
    ws = wb.create_sheet("Salden je Konto")
    spalten = [("Konto", 10), ("Bezeichnung", 30), ("Kontengruppen", 26),
               ("Soll (EUR)", 14), ("Haben (EUR)", 14), ("Saldo (EUR)", 14),
               ("Saldo netto (EUR)*", 15)]
    if ctx.susa_vj is not None:
        spalten.append(("Saldo Vorjahr (SuSa)", 16))
    spalten.append(("Buchungen", 10))
    _kopfzeile(ws, spalten)
    zeile = 2
    for k in sorted(ctx.anzahl):
        _zelle(ws, zeile, 1, k)
        _zelle(ws, zeile, 2, ctx.name(k), wrap=True)
        _zelle(ws, zeile, 3, ", ".join(ctx.plan.gruppen_von(k)), wrap=True)
        _zelle(ws, zeile, 4, float(ctx.soll[k]), fmt="#,##0.00")
        _zelle(ws, zeile, 5, float(ctx.haben[k]), fmt="#,##0.00")
        _zelle(ws, zeile, 6, float(ctx.saldo[k]), fmt="#,##0.00")
        _zelle(ws, zeile, 7, float(ctx.saldo_netto[k]), fmt="#,##0.00")
        spalte = 8
        if ctx.susa_vj is not None:
            vj = ctx.susa_vj.get(k)
            _zelle(ws, zeile, spalte, float(vj) if vj is not None else None,
                   fmt="#,##0.00")
            spalte += 1
        _zelle(ws, zeile, spalte, ctx.anzahl[k])
        zeile += 1
    _zelle(ws, zeile + 1, 1,
           "* Saldo netto: um rechnerisch abgeleitete USt/VSt bereinigt "
           "(nur GuV-/AV-Seite relevant); Bestandskonten brutto = netto.",
           wrap=True).font = Font(name=FONT, size=9, italic=True, color="595959")


def schreibe_bericht(pfad, ctx: Kontext, befunde: list[Befund],
                     kandidaten: list[dict], meta: dict) -> None:
    wb = Workbook()
    _uebersicht(wb.active, ctx, befunde, meta)
    _befundblatt(wb, "Alle Befunde", befunde, ctx)
    for bereich, blatt in BLATT_NAMEN.items():
        teil = [f for f in befunde if f.bereich == bereich]
        if teil:
            _befundblatt(wb, blatt, teil, ctx)
    _kandidatenblatt(wb, kandidaten, ctx)
    _opos_aging(wb, ctx)
    _saldenblatt(wb, ctx)
    wb.save(pfad)
