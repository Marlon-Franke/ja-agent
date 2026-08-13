"""Statistische/strukturelle Checks: Doppelbuchungen, Ausreißer, runde
Beträge, Sonn-/Feiertage, Belegdisziplin, Zeitraum, Schwellen-Splitting,
Benford, Datenqualität."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from befunde import Befund, Kontext, eur
from checks import _b, _limit, _q, _rest


def st_01_doppelbuchungen(ctx: Kontext) -> list[Befund]:
    fenster = int(ctx.param["doppel_fenster_tage"])
    minimum = Decimal(str(ctx.param["doppel_min_eur"]))
    gruppen: dict[tuple, list] = defaultdict(list)
    for b in ctx.buchungen:
        if b.umsatz >= minimum and not ctx.ist_eb(b) and b.belegdatum:
            gruppen[(b.umsatz, b.konto, b.gegenkonto)].append(b)
    out, uebrig = [], 0
    limit = _limit(ctx)
    for (_betrag, _k, _g), bs in gruppen.items():
        if len(bs) < 2:
            continue
        bs.sort(key=lambda b: b.belegdatum)
        treffer = 0
        for a, c in zip(bs, bs[1:]):
            if (c.belegdatum - a.belegdatum).days > fenster:
                continue
            if a.storno or c.storno:
                continue  # gewollte Generalumkehr
            gleicher_beleg = bool(a.belegfeld1) and a.belegfeld1 == c.belegfeld1
            schwere = "hoch" if gleicher_beleg else "mittel"
            treffer += 1
            if treffer > 3 or len(out) >= limit:
                uebrig += 1
                continue
            out.append(_b(ctx, "ST-01", schwere,
                f"Zwei Buchungen über {eur(a.umsatz)} EUR auf "
                f"{ctx.kontotext(a.konto)} an {ctx.kontotext(a.gegenkonto)} "
                f"am {a.belegdatum:%d.%m.%Y} und {c.belegdatum:%d.%m.%Y}"
                f"{' mit identischem Beleg ' + repr(a.belegfeld1) if gleicher_beleg else ''}.",
                "Doppelerfassung prüfen; ggf. eine Buchung stornieren.",
                konto=a.konto, gegenkonto=a.gegenkonto, datum=c.belegdatum,
                betrag=a.umsatz, beleg=c.belegfeld1,
                buchungstext=c.buchungstext,
                quelle=f"{_q(a)} / {_q(c)}", llm=True))
    _rest(ctx, out, "ST-01", uebrig, "Verdachtspaare")
    return out


def st_02_ausreisser(ctx: Kontext) -> list[Befund]:
    min_n = int(ctx.param["ausreisser_min_n"])
    z_grenze = float(ctx.param["ausreisser_z"])
    min_eur = Decimal(str(ctx.param["ausreisser_min_eur"]))
    out = []
    for k in sorted(ctx.anzahl):
        if not (ctx.plan.ist_guv(k) or ctx.plan.ist_av(k)):
            continue
        bew = [(d, z, w, b) for d, z, w, b in ctx.bewegungen[k] if not ctx.ist_eb(b)]
        werte = [float(abs(w)) for _d, _z, w, _b_ in bew]
        if len(werte) < min_n:
            continue
        med = median(werte)
        mad = median([abs(x - med) for x in werte])
        treffer = 0
        for d, _z, w, b in bew:
            x = float(abs(w))
            if abs(w) < min_eur:
                continue
            if mad > 0:
                auffaellig = 0.6745 * (x - med) / mad > z_grenze
            else:
                auffaellig = med > 0 and x > 8 * med
            if auffaellig:
                treffer += 1
                if treffer > 3:
                    break
                out.append(_b(ctx, "ST-02", "mittel",
                    f"Betragsausreißer auf {ctx.kontotext(k)}: {eur(abs(w))} EUR "
                    f"(Median des Kontos {eur(med)} EUR, {len(werte)} Buchungen).",
                    "Beleg einsehen: Einmaleffekt, Fehlbuchung oder "
                    "periodenfremder Aufwand?",
                    konto=k, datum=d, betrag=abs(w), beleg=b.belegfeld1,
                    buchungstext=b.buchungstext, quelle=_q(b), llm=True))
    return out


def st_03_runde_betraege(ctx: Kontext) -> list[Befund]:
    minimum = Decimal(str(ctx.param["runde_min_eur"]))
    teiler = int(ctx.param["runde_teiler"]) * 100
    haeufung_ab = int(ctx.param["runde_haeufung_ab"])
    kandidaten: list[tuple] = []
    serien: dict[tuple, list] = defaultdict(list)
    for b in ctx.buchungen:
        if ctx.ist_eb(b) or b.umsatz < minimum:
            continue
        if int(b.umsatz * 100) % teiler != 0:
            continue
        if ctx.plan.steuer(b) is not None:
            continue  # mit Steuerschlüssel sind glatte Bruttobeträge unüblich genug
        guv = b.konto if ctx.plan.ist_guv(b.konto) else (
            b.gegenkonto if ctx.plan.ist_guv(b.gegenkonto) else None)
        if guv is None or ctx.plan.in_gruppe(guv, "afa"):
            continue  # planmäßige AfA ist häufig glatt
        kandidaten.append((b, guv))
        if b.belegdatum:
            serien[(b.umsatz, b.konto, b.gegenkonto)].append(b.belegdatum)
    je_konto: Counter = Counter()
    out = []
    for b, guv in kandidaten:
        daten = serien.get((b.umsatz, b.konto, b.gegenkonto), [])
        if len(daten) >= 4 and (max(daten) - min(daten)).days >= 60:
            continue  # Dauerbuchung (Miete, Raten): glatter Betrag ist üblich
        je_konto[guv] += 1
        if je_konto[guv] <= 5:
            out.append(_b(ctx, "ST-03", "hinweis",
                f"Glatter Betrag {eur(b.umsatz)} EUR ohne Steuerschlüssel auf "
                f"{ctx.kontotext(guv)}.",
                "Beleg prüfen: Pauschale, Schätzung, Privatvorgang oder "
                "fehlender Steuerschlüssel?",
                konto=guv, datum=b.belegdatum, betrag=b.umsatz,
                beleg=b.belegfeld1, buchungstext=b.buchungstext,
                quelle=_q(b), llm=True))
    for konto, anz in je_konto.items():
        if anz >= haeufung_ab:
            out.append(_b(ctx, "ST-03", "mittel",
                f"Häufung glatter Beträge auf {ctx.kontotext(konto)}: "
                f"{anz} Buchungen ≥ {eur(minimum)} EUR.",
                "Systematik klären (Abschlagszahlungen, Pauschalen, "
                "Schätzbuchungen).", konto=konto))
    return out


def _ostern(jahr: int) -> date:
    a, b, c = jahr % 19, jahr // 100, jahr % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    monat = (h + l - 7 * m + 114) // 31
    tag = ((h + l - 7 * m + 114) % 31) + 1
    return date(jahr, monat, tag)


def feiertage(jahr: int, zusatz: list[str] | None = None) -> set[date]:
    """Bundesweit einheitliche Feiertage. Landesfeiertage über `zusatz`
    (Parameter `feiertage_zusatz`): feste Tage als "MM-TT" sowie die
    beweglichen Schlüsselwörter "fronleichnam" (Ostersonntag + 60) und
    "buss_und_bettag" (Mittwoch vor dem 23.11.)."""
    o = _ostern(jahr)
    tage = {date(jahr, 1, 1), o - timedelta(days=2), o + timedelta(days=1),
            date(jahr, 5, 1), o + timedelta(days=39), o + timedelta(days=50),
            date(jahr, 10, 3), date(jahr, 12, 25), date(jahr, 12, 26)}
    for eintrag in zusatz or []:
        if eintrag == "fronleichnam":
            tage.add(o + timedelta(days=60))
        elif eintrag == "buss_und_bettag":
            d = date(jahr, 11, 22)
            while d.weekday() != 2:
                d -= timedelta(days=1)
            tage.add(d)
        else:
            monat, tag = eintrag.split("-")
            tage.add(date(jahr, int(monat), int(tag)))
    return tage


def st_04_sonn_feiertage(ctx: Kontext) -> list[Befund]:
    jahre = {d.year for d in (ctx.datum_von, ctx.datum_bis) if d}
    frei: set[date] = set()
    zusatz = ctx.param.get("feiertage_zusatz", [])
    for j in jahre:
        frei |= feiertage(j, zusatz)
    je_konto: dict[int, list] = defaultdict(list)
    for k in ctx.konten_in("kasse"):
        for d, _z, w, b in ctx.bewegungen[k]:
            if d and not ctx.ist_eb(b) and (d.weekday() == 6 or d in frei):
                je_konto[k].append((d, w))
    out = []
    for k, eintraege in je_konto.items():
        beispiele = ", ".join(f"{d:%d.%m.%Y}" for d, _w in eintraege[:3])
        summe = sum((abs(w) for _d, w in eintraege), Decimal(0))
        out.append(_b(ctx, "ST-04", "hinweis",
            f"Kassenkonto {ctx.kontotext(k)}: {len(eintraege)} Buchung(en) an "
            f"Sonn-/Feiertagen (u. a. {beispiele}), Summe {eur(summe)} EUR.",
            "Mit Öffnungszeiten/Geschäftsmodell abgleichen; bei geschlossenem "
            "Betrieb Belegdaten hinterfragen.", konto=k, betrag=summe))
    return out


def st_05_belegdisziplin(ctx: Kontext) -> list[Befund]:
    basis = [b for b in ctx.buchungen if not ctx.ist_eb(b)]
    if not basis:
        return []
    quote_warn = float(ctx.param["belegfeld_quote_warn"])
    out = []
    for feld, bezeichnung in (("belegfeld1", "Belegfeld 1 (Belegnummer)"),
                              ("buchungstext", "Buchungstext")):
        leer = sum(1 for b in basis if not getattr(b, feld).strip())
        quote = leer / len(basis)
        if quote > quote_warn:
            out.append(_b(ctx, "ST-05", "hinweis",
                f"{leer} von {len(basis)} Buchungen ({quote:.0%}) ohne "
                f"{bezeichnung}.",
                "Belegdisziplin/GoBD-Nachvollziehbarkeit verbessern; "
                "Kontierungsrichtlinie schärfen."))
    return out


def st_06_zeitraum(ctx: Kontext) -> list[Befund]:
    if not (ctx.datum_von and ctx.datum_bis):
        ctx.skip("ST-06", "Header-Zeitraum (Datum von/bis) fehlt")
        return []
    out, uebrig = [], 0
    limit = _limit(ctx)
    for b in ctx.buchungen:
        if b.belegdatum and not (ctx.datum_von <= b.belegdatum <= ctx.datum_bis):
            if len(out) >= limit:
                uebrig += 1
                continue
            out.append(_b(ctx, "ST-06", "mittel",
                f"Belegdatum {b.belegdatum:%d.%m.%Y} außerhalb des "
                f"Stapelzeitraums ({ctx.datum_von:%d.%m.%Y}–"
                f"{ctx.datum_bis:%d.%m.%Y}).",
                "Periodenzuordnung prüfen (Abgrenzung, falsches Belegdatum).",
                konto=b.konto, datum=b.belegdatum, betrag=b.umsatz,
                beleg=b.belegfeld1, buchungstext=b.buchungstext, quelle=_q(b)))
    _rest(ctx, out, "ST-06", uebrig, "Buchungen außerhalb des Zeitraums")
    return out


def st_07_splitting(ctx: Kontext) -> list[Befund]:
    grenze = Decimal(str(ctx.param["gwg_grenze_netto"]))
    band = Decimal(str(ctx.param["splitting_band"]))
    fenster = int(ctx.param["splitting_fenster_tage"])
    gruppen: dict[tuple, list] = defaultdict(list)
    for gruppe in ("av_abnutzbar", "gwg"):
        for k in ctx.konten_in(gruppe):
            for d, _z, w, b in ctx.bewegungen[k]:
                if w <= 0 or ctx.ist_eb(b) or d is None:
                    continue
                netto = ctx.plan.netto(b)
                if band * grenze <= netto <= grenze:
                    gruppen[(k, b.gegenkonto if b.konto == k else b.konto)].append((d, netto, b))
    out = []
    for (konto, gegen), eintraege in gruppen.items():
        if len(eintraege) < 2:
            continue
        eintraege.sort()
        if any((b_ - a).days <= fenster for (a, _n1, _b1), (b_, _n2, _b2)
               in zip(eintraege, eintraege[1:])):
            summe = sum((n for _d, n, _b_ in eintraege), Decimal(0))
            out.append(_b(ctx, "ST-07", "hinweis",
                f"{len(eintraege)} Zugänge knapp unter der GWG-Grenze auf "
                f"{ctx.kontotext(konto)} (Gegenkonto {gegen}) binnen kurzer "
                f"Zeit, Summe netto {eur(summe)} EUR.",
                "Künstliche Aufteilung eines einheitlichen Wirtschaftsguts "
                "ausschließen (Bewertungseinheit).",
                konto=konto, datum=eintraege[0][0], betrag=summe, llm=True))
    return out


_BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def st_08_benford(ctx: Kontext) -> list[Befund]:
    min_n = int(ctx.param["benford_min_n"])
    werte = []
    for b in ctx.buchungen:
        if ctx.ist_eb(b) or b.umsatz < 10:
            continue
        if ctx.plan.ist_guv(b.konto) or ctx.plan.ist_guv(b.gegenkonto):
            werte.append(b.umsatz)
    if len(werte) < min_n:
        ctx.skip("ST-08", f"zu wenige GuV-Buchungen für Benford ({len(werte)} < {min_n})")
        return []
    zaehler = Counter(str(w).lstrip("0.,")[0] for w in werte)
    n = len(werte)
    abweichungen = {d: zaehler.get(str(d), 0) / n - _BENFORD[d] for d in range(1, 10)}
    mad = sum(abs(v) for v in abweichungen.values()) / 9
    if mad > float(ctx.param["benford_mad_grenze"]):
        top = sorted(abweichungen.items(), key=lambda e: -abs(e[1]))[:3]
        details = ", ".join(
            f"Ziffer {d}: {zaehler.get(str(d), 0) / n:.1%} statt {_BENFORD[d]:.1%}"
            for d, _v in top)
        return [_b(ctx, "ST-08", "hinweis",
            f"Erstziffern-Verteilung weicht von Benford ab "
            f"(MAD {mad:.4f}, n={n}): {details}.",
            "Nur Indiz: Häufungen können aus Preisstruktur/Dauerbuchungen "
            "stammen; auffällige Ziffernbereiche stichprobenhaft prüfen.")]
    return []


def dq_01_datenqualitaet(ctx: Kontext) -> list[Befund]:
    if not ctx.warnungen:
        return []
    beispiele = "; ".join(ctx.warnungen[:5])
    return [_b(ctx, "DQ-01", "hinweis",
        f"{len(ctx.warnungen)} Zeile(n) beim Import übersprungen oder "
        f"beanstandet. Beispiele: {beispiele}",
        "Quelldatei prüfen; betroffene Zeilen sind nicht in die Prüfung "
        "eingeflossen.")]


ALLE_STATISTIK = [
    st_01_doppelbuchungen, st_02_ausreisser, st_03_runde_betraege,
    st_04_sonn_feiertage, st_05_belegdisziplin, st_06_zeitraum,
    st_07_splitting, st_08_benford, dq_01_datenqualitaet,
]
