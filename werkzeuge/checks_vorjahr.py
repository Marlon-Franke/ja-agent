"""Vorjahresvergleich auf Basis einer Vorjahres-SuSa (--susa-vorjahr).

VJ-01: Bilanzidentität – EB-Werte des Prüfjahres (aus den
Saldovortragsbuchungen des Stapels) gegen die Schlussbestände der
Vorjahres-SuSa (§ 252 Abs. 1 Nr. 1 HGB). Deckt zugleich: EB-Wert fehlt
trotz Vorjahresbestand, EB ohne Vorjahresbestand (neues Konto).

VJ-02: GuV-Konten gegen Vorjahr – erstmalig wesentlich bebucht,
weggefallen, Vorzeichenwechsel, starke Veränderung.
"""

from __future__ import annotations

from decimal import Decimal

from befunde import Befund, Kontext, eur
from checks import _b, _limit, _rest

_VJ01_UEBERSPRINGEN = ("saldovortrag", "steuer_vst", "steuer_ust", "steuer_vz")


def vj_01_eb_abgleich(ctx: Kontext) -> list[Befund]:
    if ctx.susa_vj is None:
        ctx.skip("VJ-01", "erfordert Vorjahres-SuSa (--susa-vorjahr)")
        return []
    if not ctx.eb_vorhanden:
        ctx.skip("VJ-01", "keine EB-/Saldovortragsbuchungen im Stapel")
        return []
    toleranz = Decimal(str(ctx.param["susa_toleranz_eur"]))
    limit = _limit(ctx)
    out, uebrig = [], 0
    for k in sorted(set(ctx.susa_vj) | set(ctx.eb_salden)):
        if ctx.plan.ist_guv(k):
            continue  # GuV-Salden werden nicht vorgetragen
        if any(ctx.plan.in_gruppe(k, g) for g in _VJ01_UEBERSPRINGEN):
            continue  # Steuerkonten: Vortragswege variieren (UStVA-Verrechnung)
        vj = ctx.susa_vj.get(k, Decimal(0))
        eb = ctx.eb_salden.get(k, Decimal(0))
        if abs(vj) <= ctx.bagatelle and abs(eb) <= ctx.bagatelle:
            continue
        diff = eb - vj
        if abs(diff) <= toleranz:
            continue
        if len(out) >= limit:
            uebrig += 1
            continue
        kapitalnah = (ctx.plan.in_gruppe(k, "eigenkapital")
                      or ctx.plan.in_gruppe(k, "privat"))
        if abs(eb) <= ctx.bagatelle:
            text = (f"Konto {ctx.kontotext(k)}: Vorjahres-Schlussbestand "
                    f"{eur(vj)} EUR, aber kein EB-Wert übernommen.")
        elif abs(vj) <= ctx.bagatelle:
            text = (f"Konto {ctx.kontotext(k)}: EB-Wert {eur(eb)} EUR ohne "
                    "Vorjahres-Schlussbestand (neues Konto oder "
                    "Umgliederung?).")
        else:
            text = (f"Konto {ctx.kontotext(k)}: EB-Wert {eur(eb)} EUR weicht "
                    f"vom Vorjahres-Schlussbestand {eur(vj)} EUR ab "
                    f"(Differenz {eur(diff)} EUR).")
        out.append(_b(ctx, "VJ-01", "hinweis" if kapitalnah else "mittel",
            text,
            "Bilanzidentität wahren (§ 252 Abs. 1 Nr. 1 HGB): EB-Übernahme "
            "prüfen." + (" Bei Kapital-/Privatkonten kann die Differenz aus "
                         "Ergebnisverwendung/Umbuchung stammen."
                         if kapitalnah else ""),
            konto=k, betrag=diff))
    _rest(ctx, out, "VJ-01", uebrig, "EB-Abweichungen")
    return out


def vj_02_guv_vergleich(ctx: Kontext) -> list[Befund]:
    if ctx.susa_vj is None:
        ctx.skip("VJ-02", "erfordert Vorjahres-SuSa (--susa-vorjahr)")
        return []
    minimum = Decimal(str(ctx.param["vj_min_eur"]))
    faktor = Decimal(str(ctx.param["vj_faktor"]))
    limit = _limit(ctx)
    treffer: list[tuple[Decimal, Befund]] = []
    konten = {k for k in ctx.susa_vj if ctx.plan.ist_guv(k)}
    konten |= {k for k in ctx.anzahl if ctx.plan.ist_guv(k)}
    for k in sorted(konten):
        alt = ctx.susa_vj.get(k, Decimal(0))
        neu = ctx.saldo_netto.get(k, Decimal(0))
        if abs(alt) <= ctx.bagatelle and abs(neu) <= ctx.bagatelle:
            continue
        diff = neu - alt
        if abs(alt) <= ctx.bagatelle and abs(neu) >= minimum:
            text = (f"Konto {ctx.kontotext(k)} erstmalig wesentlich bebucht: "
                    f"{eur(neu)} EUR (Vorjahr 0).")
        elif abs(neu) <= ctx.bagatelle and abs(alt) >= minimum:
            text = (f"Konto {ctx.kontotext(k)} im Vorjahr mit {eur(alt)} EUR, "
                    "im Prüfjahr ohne Saldo.")
        elif alt * neu < 0 and max(abs(alt), abs(neu)) >= minimum:
            text = (f"Konto {ctx.kontotext(k)} mit Vorzeichenwechsel: "
                    f"{eur(alt)} EUR (VJ) zu {eur(neu)} EUR.")
        elif (abs(diff) >= minimum
              and (abs(neu) > faktor * abs(alt) or abs(neu) * faktor < abs(alt))):
            text = (f"Konto {ctx.kontotext(k)}: starke Veränderung von "
                    f"{eur(alt)} EUR (VJ) auf {eur(neu)} EUR "
                    f"(Differenz {eur(diff)} EUR).")
        else:
            continue
        treffer.append((abs(diff), _b(ctx, "VJ-02", "hinweis", text,
            "Ursache würdigen: Geschäftsentwicklung, Umkontierung, "
            "Periodenverschiebung oder Fehlbuchung.",
            konto=k, betrag=diff)))
    treffer.sort(key=lambda e: -e[0])
    out = [b for _d, b in treffer[:limit]]
    _rest(ctx, out, "VJ-02", max(0, len(treffer) - limit), "Vorjahresabweichungen")
    return out


ALLE_VORJAHR = [vj_01_eb_abgleich, vj_02_guv_vergleich]
