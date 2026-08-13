"""Vereinfachte Bilanz-/GuV-Positionszuordnung je Konto.

Grundlage sind die Kontengruppen aus konten_config.json; die Zuordnung
orientiert sich an § 266 / § 275 HGB, bewusst vergröbert (die amtliche
Gliederungstiefe erfordert eine Positions-Zuordnungstabelle je Konto -
Ausbaustufe, siehe Prüfkatalog Kap. 17). Das Eigenkapital ist nach
§ 266 Abs. 3 A. HGB untergliedert (A.I-A.V); der Ausweis erfolgt stets
VOR Ergebnisverwendung (nach teilweiser/vollständiger Verwendung träte
gemäß § 268 Abs. 1 HGB "Bilanzgewinn/Bilanzverlust" an die Stelle von
A.IV/A.V). A.V (Jahresüberschuss/Jahresfehlbetrag) ist keinem Konto
zugeordnet, sondern wird als GuV-Summe ausgewiesen (Excel: Formel auf
das GuV-Blatt; salden.csv: synthetische "(ergebnis)"-Zeile). Personen-
und Steuerkonten sowie Misch-/Restkonten werden nach Saldenlage der
Aktiv- bzw. Passivseite zugewiesen; die Blätter Bilanz/GuV im Bericht
aggregieren per SUMIF-Formel über diese Positionen und bleiben damit
live mit dem Blatt "Salden je Konto" verknüpft.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from befunde import Kontext

VORTRAG = "Z. Saldenvortrags-Differenz (SB-06)"
ERGEBNIS = "A.V. Jahresüberschuss/Jahresfehlbetrag"

AKTIV = [
    "A. Anlagevermögen",
    "B.I. Forderungen aus Lieferungen und Leistungen",
    "B.II. Forderungen gegen Gesellschafter",
    "B.III. Kasse, Bank, Geldtransit",
    "C. Aktive Rechnungsabgrenzung",
    "D. Aktive latente Steuern",
    "E. Sonstige Aktiva",
]
# Eigenkapital-Schemata je Rechtsform (DATEV-Kontenzuordnung siehe
# Prüfkatalog "Formatreferenzen"; Rechtsform aus Parameter/--rechtsform):
# Kapitalgesellschaft nach § 266 Abs. 3 A. HGB, Personengesellschaft mit
# Kapitalanteilen je Haftungsgruppe (DATEV-KKE-Kontenwelt vereinfacht),
# Einzelunternehmen als eine Position (§ 247 Abs. 1 HGB).
PASSIV_EK_KAPG = [
    "A.I. Gezeichnetes Kapital",
    "A.II. Kapitalrücklage",
    "A.III. Gewinnrücklagen",
    "A.IV. Gewinn-/Verlustvortrag",
]
PASSIV_EK_PERSG = [
    "A.I. Kapitalanteile persönlich haftende Gesellschafter",
    "A.II. Kapitalanteile Kommanditisten",
    "A.III. Rücklagen",
    "A.IV. Gewinn-/Verlustvortrag",
]
PASSIV_EK_EU = ["A. Eigenkapital (Einzelunternehmen)"]
EK_UEBRIG = "A.VI. Übriges Eigenkapital (Privat-/sonstige EK-Konten)"
EK_KKE = "A.VII. KKE-/Umbuchungskonten Kapital (Klasse 9)"
PASSIV_FK = [
    "B. Rückstellungen",
    "C.I. Verbindlichkeiten gegenüber Kreditinstituten",
    "C.II. Verbindlichkeiten aus Lieferungen und Leistungen",
    "C.III. Verbindlichkeiten gegenüber Gesellschaftern",
    "C.IV. Sonstige Verbindlichkeiten",
    "D. Passive Rechnungsabgrenzung",
    "E. Passive latente Steuern",
]
# Union aller möglichen Konten-Positionen der Passivseite (ohne
# synthetisches A.V) - Basis für Bilanzprobe und BI-Filterlisten.
# dict.fromkeys dedupliziert schema-übergreifend identische Labels
# (z. B. A.IV in KapG- und PersG-Schema), sonst zählte die Probe doppelt.
PASSIV = list(dict.fromkeys(
    PASSIV_EK_EU + PASSIV_EK_KAPG + PASSIV_EK_PERSG
    + [EK_UEBRIG, EK_KKE] + PASSIV_FK))


def _rechtsform(ctx: Kontext) -> str:
    return str(ctx.param.get("rechtsform", "")).lower()


def passiv_ek(ctx: Kontext) -> list[str]:
    """EK-Positionsliste des aktiven Rechtsform-Schemas (ohne A.V);
    ohne Rechtsform-Angabe gilt das § 266-Schema der KapG."""
    rf = _rechtsform(ctx)
    if rf == "einzelunternehmen":
        return PASSIV_EK_EU
    if rf == "personengesellschaft":
        return PASSIV_EK_PERSG
    return PASSIV_EK_KAPG


def passiv_uebrig(ctx: Kontext) -> list[str]:
    rf = _rechtsform(ctx)
    if rf == "einzelunternehmen":
        return PASSIV_FK
    if rf == "personengesellschaft":
        return [EK_UEBRIG, EK_KKE] + PASSIV_FK
    return [EK_UEBRIG] + PASSIV_FK
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


def position(ctx: Kontext, konto: int, saldo: Decimal | None = None) -> str:
    """Positionszuordnung; saldo-Override für Konten ohne
    Berichtsjahresbewegung (z. B. reine Vorjahreskonten), damit die
    Saldenlage-Fallbacks nach dem maßgeblichen Saldo entscheiden."""
    plan = ctx.plan
    if saldo is None:
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
    ek_artig = (g("gezeichnetes_kapital") or g("kapitalruecklage")
                or g("gewinnruecklagen") or g("gewinn_verlustvortrag")
                or g("kapital_vollhafter") or g("kapital_teilhafter")
                or g("kapital_kke") or g("eigenkapital") or g("privat"))
    if ek_artig:
        rf = _rechtsform(ctx)
        if rf == "einzelunternehmen":
            return PASSIV_EK_EU[0]
        if rf == "personengesellschaft":
            if g("kapital_vollhafter"):
                return "A.I. Kapitalanteile persönlich haftende Gesellschafter"
            if g("kapital_teilhafter"):
                return "A.II. Kapitalanteile Kommanditisten"
            if g("kapitalruecklage") or g("gewinnruecklagen"):
                return "A.III. Rücklagen"
            if g("gewinn_verlustvortrag"):
                return "A.IV. Gewinn-/Verlustvortrag"
            if g("kapital_kke"):
                return EK_KKE
            return EK_UEBRIG
        # Kapitalgesellschaft (und Default ohne Rechtsform-Angabe)
        if g("gezeichnetes_kapital"):
            return "A.I. Gezeichnetes Kapital"
        if g("kapitalruecklage"):
            return "A.II. Kapitalrücklage"
        if g("gewinnruecklagen"):
            return "A.III. Gewinnrücklagen"
        if g("gewinn_verlustvortrag"):
            return "A.IV. Gewinn-/Verlustvortrag"
        return EK_UEBRIG
    if g("gesellschafter"):
        return ("B.II. Forderungen gegen Gesellschafter" if saldo >= 0
                else "C.III. Verbindlichkeiten gegenüber Gesellschaftern")
    if g("lst_sv_verb") or g("steuer_ust") or g("steuer_vz"):
        return "C.IV. Sonstige Verbindlichkeiten"
    if plan.ist_av(konto) or g("grund_boden"):
        return "A. Anlagevermögen"
    return ("E. Sonstige Aktiva" if saldo >= 0
            else "C.IV. Sonstige Verbindlichkeiten")


def summen(ctx: Kontext) -> dict:
    """Positionssummen (saldo_netto) für Berichtsjahr [0] und Vorjahr [1]
    auf exakt der Datenbasis, die salden.csv und das Blatt "Salden je
    Konto" ausweisen (Konten, Vorjahres-only-Konten, implizite USt/VSt-
    Zeilen). Liefert zusätzlich das GuV-Ergebnis (als saldo_netto-Summe:
    Verlust positiv), die Bilanzsummen beider Seiten und die Bilanzprobe
    Aktiva - Passiva (Soll: 0,00 in beiden Jahren)."""
    je_pos: dict[str, list[Decimal]] = defaultdict(
        lambda: [Decimal(0), Decimal(0)])
    for k in ctx.anzahl:
        je_pos[position(ctx, k)][0] += ctx.saldo_netto[k]
    if ctx.susa_vj:
        for k, s in ctx.susa_vj.items():
            pos = (position(ctx, k) if k in ctx.anzahl
                   else position(ctx, k, saldo=s))
            je_pos[pos][1] += s
    if ctx.vst_rechnerisch is not None:
        je_pos["E. Sonstige Aktiva"][0] += ctx.vst_rechnerisch
        je_pos["C.IV. Sonstige Verbindlichkeiten"][0] -= ctx.ust_rechnerisch
    ergebnis = [sum((je_pos[p][i] for p in GUV), Decimal(0))
                for i in (0, 1)]
    aktiva = [sum((je_pos[p][i] for p in AKTIV), Decimal(0))
              for i in (0, 1)]
    passiva = [-(sum((je_pos[p][i] for p in PASSIV), Decimal(0))
                 + ergebnis[i] + je_pos[VORTRAG][i]) for i in (0, 1)]
    return {
        "je_position": dict(je_pos),
        "ergebnis": ergebnis,          # saldo_netto-Logik (Verlust > 0)
        "aktiva": aktiva,
        "passiva": passiva,            # Ausweisrichtung (Haben > 0)
        "probe": [aktiva[i] - passiva[i] for i in (0, 1)],
    }
