"""Vereinfachte Bilanz-/GuV-Positionszuordnung je Konto.

Grundlage sind die Kontengruppen aus konten_config.json; die Zuordnung
orientiert sich an § 266 / § 275 HGB, bewusst vergröbert (die amtliche
Gliederungstiefe erfordert eine Positions-Zuordnungstabelle je Konto -
Ausbaustufe, siehe Prüfkatalog Kap. 17). Personen- und Steuerkonten sowie
Misch-/Restkonten werden nach Saldenlage der Aktiv- bzw. Passivseite
zugewiesen; die Blätter Bilanz/GuV im Bericht aggregieren per
SUMIF-Formel über diese Positionen und bleiben damit live mit dem Blatt
"Salden je Konto" verknüpft.
"""

from __future__ import annotations

from decimal import Decimal

from befunde import Kontext

VORTRAG = "(Saldenvortrags-Differenz)"

AKTIV = [
    "A. Anlagevermögen",
    "B.I. Forderungen aus Lieferungen und Leistungen",
    "B.II. Forderungen gegen Gesellschafter",
    "B.III. Kasse, Bank, Geldtransit",
    "C. Aktive Rechnungsabgrenzung",
    "D. Aktive latente Steuern",
    "E. Sonstige Aktiva",
]
PASSIV = [
    "A. Eigenkapital",
    "B. Rückstellungen",
    "C.I. Verbindlichkeiten gegenüber Kreditinstituten",
    "C.II. Verbindlichkeiten aus Lieferungen und Leistungen",
    "C.III. Verbindlichkeiten gegenüber Gesellschaftern",
    "C.IV. Sonstige Verbindlichkeiten",
    "D. Passive Rechnungsabgrenzung",
    "E. Passive latente Steuern",
]
GUV_ERTRAG = ["1. Umsatzerlöse", "3. Sonstige betriebliche Erträge"]
GUV = [
    "1. Umsatzerlöse",
    "2. Erlösschmälerungen",
    "3. Sonstige betriebliche Erträge",
    "4. Materialaufwand",
    "5. Personalaufwand",
    "6. Abschreibungen",
    "7. Sonstige betriebliche Aufwendungen",
    "8. Zinsen und ähnliche Aufwendungen",
    "9. Steuern vom Einkommen und vom Ertrag",
]


def position(ctx: Kontext, konto: int) -> str:
    plan = ctx.plan
    saldo = ctx.saldo_netto.get(konto, Decimal(0))

    def g(name: str) -> bool:
        return plan.in_gruppe(konto, name)

    if g("saldovortrag"):
        return VORTRAG
    if plan.ist_guv(konto):
        if g("afa"):
            return "6. Abschreibungen"
        if g("kst_aufwand"):
            return "9. Steuern vom Einkommen und vom Ertrag"
        if g("zinsaufwand"):
            return "8. Zinsen und ähnliche Aufwendungen"
        if g("material"):
            return "4. Materialaufwand"
        if g("lohn"):
            return "5. Personalaufwand"
        if g("erloesschmaelerung"):
            return "2. Erlösschmälerungen"
        if g("ertrag"):
            return "1. Umsatzerlöse"
        if saldo < 0:
            return "3. Sonstige betriebliche Erträge"
        return "7. Sonstige betriebliche Aufwendungen"
    if plan.ist_debitor(konto) or g("forderungen_sammel"):
        return "B.I. Forderungen aus Lieferungen und Leistungen"
    if plan.ist_kreditor(konto):
        return "C.II. Verbindlichkeiten aus Lieferungen und Leistungen"
    if g("kasse") or g("bank") or g("geldtransit"):
        return "B.III. Kasse, Bank, Geldtransit"
    if g("rap_aktiv"):
        return "C. Aktive Rechnungsabgrenzung"
    if g("rap_passiv"):
        return "D. Passive Rechnungsabgrenzung"
    if g("latente_steuern"):
        return ("D. Aktive latente Steuern" if saldo >= 0
                else "E. Passive latente Steuern")
    if g("rueckstellungen"):
        return "B. Rückstellungen"
    if g("darlehen"):
        return "C.I. Verbindlichkeiten gegenüber Kreditinstituten"
    if g("eigenkapital") or g("privat"):
        return "A. Eigenkapital"
    if g("gesellschafter"):
        return ("B.II. Forderungen gegen Gesellschafter" if saldo >= 0
                else "C.III. Verbindlichkeiten gegenüber Gesellschaftern")
    if g("lst_sv_verb") or g("steuer_ust") or g("steuer_vz"):
        return "C.IV. Sonstige Verbindlichkeiten"
    if plan.ist_av(konto) or g("grund_boden"):
        return "A. Anlagevermögen"
    return ("E. Sonstige Aktiva" if saldo >= 0
            else "C.IV. Sonstige Verbindlichkeiten")
