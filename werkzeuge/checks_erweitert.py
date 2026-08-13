"""Erweiterte Checks nach dem Prüfkatalog: Datenintegrität, Kasse,
USt-Erweiterungen, Kreditoren, OPOS-Abgleich, sonstige Bilanzkonten,
GuV-Plausibilitäten, Ertragsteuer, Cut-off, Gesellschafter,
Fraud-Indikatoren, Stammdaten."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal
from statistics import median

from befunde import Befund, Kontext, eur
from checks import _b, _limit, _q, _rest


# ------------------------------------------------- Datenintegrität (Ebene 1)

def dv_01_nullwerte(ctx: Kontext) -> list[Befund]:
    nullbetraege = [b for b in ctx.buchungen if b.umsatz == 0]
    gleichkonto = [b for b in ctx.buchungen if b.konto == b.gegenkonto]
    out = []
    for liste, text, empf in (
            (nullbetraege, "Buchung(en) mit Betrag 0,00",
             "Technische Leerbuchungen klären und bereinigen."),
            (gleichkonto, "Buchung(en) mit Konto = Gegenkonto",
             "Inkonsistente Buchungssätze prüfen.")):
        if liste:
            beispiel = liste[0]
            out.append(_b(ctx, "DV-01", "hinweis",
                f"{len(liste)} {text} (z. B. {_q(beispiel)}).", empf,
                konto=beispiel.konto, datum=beispiel.belegdatum,
                quelle=_q(beispiel)))
    return out


def dv_02_eb_auf_guv(ctx: Kontext) -> list[Befund]:
    out, uebrig = [], 0
    limit = _limit(ctx)
    for b in ctx.buchungen:
        if not ctx.ist_eb(b):
            continue
        guv = b.konto if ctx.plan.ist_guv(b.konto) else (
            b.gegenkonto if ctx.plan.ist_guv(b.gegenkonto) else None)
        if guv is not None:
            if len(out) >= limit:
                uebrig += 1
                continue
            out.append(_b(ctx, "DV-02", "mittel",
                f"Saldovortrag gegen GuV-Konto {ctx.kontotext(guv)} gebucht "
                f"({eur(b.umsatz)} EUR).",
                "EB-Werte dürfen nur Bilanzkonten betreffen "
                "(Bilanzidentität, § 252 Abs. 1 Nr. 1 HGB); umbuchen.",
                konto=guv, gegenkonto=b.gegenkonto if guv == b.konto else b.konto,
                datum=b.belegdatum, betrag=b.umsatz,
                buchungstext=b.buchungstext, quelle=_q(b)))
    _rest(ctx, out, "DV-02", uebrig, "EB-Buchungen auf GuV-Konten")
    return out


def dv_03_konten_ohne_namen(ctx: Kontext) -> list[Befund]:
    if not ctx.namen:
        ctx.skip("DV-03", "erfordert Kontenbeschriftungen (EXTF Kat. 20)")
        return []
    fehlend = sorted(k for k in ctx.anzahl if k not in ctx.namen
                     and not ctx.plan.in_gruppe(k, "saldovortrag"))
    if not fehlend:
        return []
    liste = ", ".join(str(k) for k in fehlend[:20])
    return [_b(ctx, "DV-03", "hinweis",
        f"{len(fehlend)} bebuchte Konten ohne Kontenbeschriftung: {liste}"
        f"{' …' if len(fehlend) > 20 else ''}.",
        "Stammdaten pflegen bzw. Fehlkontierungen auf ungenutzte Konten "
        "ausschließen.")]


# ------------------------------------------------------ Kasse (SB-09/10)

def sb_09_kassenbewegung_ausreisser(ctx: Kontext) -> list[Befund]:
    minimum = Decimal(str(ctx.param["kasse_bewegung_ausreisser_min"]))
    z_grenze = float(ctx.param["ausreisser_z"])
    out = []
    for k in ctx.konten_in("kasse"):
        bew = [(d, w, b) for d, _z, w, b in ctx.bewegungen[k] if not ctx.ist_eb(b)]
        if len(bew) < int(ctx.param["ausreisser_min_n"]):
            continue
        serien = Counter(abs(w) for _d, w, _b_ in bew)
        werte = [float(abs(w)) for _d, w, _b_ in bew]
        med = median(werte)
        mad = median([abs(x - med) for x in werte])
        treffer = 0
        for d, w, b in bew:
            x = float(abs(w))
            if abs(w) < minimum or serien[abs(w)] >= 4:
                continue  # Dauerbewegungen (regelmäßige Einzahlungen)
            auffaellig = (0.6745 * (x - med) / mad > z_grenze) if mad > 0 \
                else (med > 0 and x > 8 * med)
            if auffaellig:
                treffer += 1
                if treffer > 3:
                    break
                out.append(_b(ctx, "SB-09", "hinweis",
                    f"Ungewöhnlich hohe Kassenbewegung {eur(abs(w))} EUR "
                    f"(Median {eur(med)} EUR) auf {ctx.kontotext(k)}.",
                    "Barbeleg prüfen (hohe Bareinnahme/-ausgabe, "
                    "sprunghafte Bestandsänderung).",
                    konto=k, datum=d, betrag=abs(w), beleg=b.belegfeld1,
                    buchungstext=b.buchungstext, quelle=_q(b), llm=True))
    return out


def sb_10_glatte_barbewegungen(ctx: Kontext) -> list[Befund]:
    ab = Decimal(str(ctx.param["kasse_glatt_ab"]))
    out = []
    for b in ctx.buchungen:
        seiten = {b.konto, b.gegenkonto}
        if not any(ctx.plan.in_gruppe(k, "kasse") for k in seiten):
            continue
        if not any(ctx.plan.in_gruppe(k, "privat") for k in seiten):
            continue
        if b.umsatz >= ab and int(b.umsatz * 100) % 5000 == 0:
            out.append(_b(ctx, "SB-10", "hinweis",
                f"Glatte Barbewegung {eur(b.umsatz)} EUR zwischen Kasse und "
                f"Privat ({b.konto} an {b.gegenkonto}).",
                "Bareinlagen/-entnahmen auf Herkunft bzw. Anlass prüfen "
                "(Kassenfehlbeträge, Nachbuchungen).",
                konto=b.konto, gegenkonto=b.gegenkonto, datum=b.belegdatum,
                betrag=b.umsatz, buchungstext=b.buchungstext, quelle=_q(b),
                llm=True))
            if len(out) >= 5:
                break
    return out


# ------------------------------------------------------ USt (US-08/09/10)

def us_08_automatik_konflikt(ctx: Kontext) -> list[Befund]:
    out = []
    for b in ctx.buchungen:
        if not b.bu:
            continue
        ziffer = b.bu[-1]
        eintrag = ctx.plan.steuerschluessel.get(ziffer)
        if not eintrag:
            continue
        for konto in (b.konto, b.gegenkonto):
            erwartet = ctx.plan._automatik_satz(konto)
            if erwartet and (eintrag[0], eintrag[1]) != erwartet:
                out.append(_b(ctx, "US-08", "mittel",
                    f"BU-Schlüssel {b.bu} ({eintrag[0]} {eintrag[1]} %) auf "
                    f"Automatikkonto {ctx.kontotext(konto)} (erwartet "
                    f"{erwartet[0]} {erwartet[1]} %).",
                    "Schlüssel-/Kontenwahl klären; Automatikkonten steuern "
                    "die USt selbst (Konfliktbuchungen prüfen).",
                    konto=konto, datum=b.belegdatum, betrag=b.umsatz,
                    beleg=b.belegfeld1, buchungstext=b.buchungstext,
                    quelle=_q(b)))
                break
    return out


def us_09_schluesselwechsel_partner(ctx: Kontext) -> list[Befund]:
    min_n = int(ctx.param["schluessel_min_n"])
    dominanz = float(ctx.param["schluessel_dominanz"])
    profile: dict[int, Counter] = defaultdict(Counter)
    beispiele: dict[tuple[int, str], list] = defaultdict(list)
    for b in ctx.buchungen:
        if ctx.ist_eb(b):
            continue
        partner = b.konto if ctx.plan.ist_personenkonto(b.konto) else (
            b.gegenkonto if ctx.plan.ist_personenkonto(b.gegenkonto) else None)
        if partner is None:
            continue
        sachseite = b.gegenkonto if partner == b.konto else b.konto
        if not (ctx.plan.ist_guv(sachseite) or ctx.plan.ist_av(sachseite)):
            continue  # Zahlungen ausblenden, nur Rechnungsbuchungen
        st = ctx.plan.steuer(b)
        signatur = f"{st[0]} {st[1]} %" if st else "ohne Steuer"
        profile[partner][signatur] += 1
        if len(beispiele[(partner, signatur)]) < 2:
            beispiele[(partner, signatur)].append(b)
    out = []
    for partner, zaehler in sorted(profile.items()):
        n = sum(zaehler.values())
        if n < min_n:
            continue
        (top_sig, top_n), = zaehler.most_common(1)
        if top_n / n >= dominanz and top_n < n:
            details = []
            for sig, _anz in zaehler.items():
                if sig == top_sig:
                    continue
                for b in beispiele[(partner, sig)]:
                    datum = f"{b.belegdatum:%d.%m.%Y}" if b.belegdatum else "?"
                    details.append(f"{datum} {eur(b.umsatz)} EUR [{sig}]")
            out.append(_b(ctx, "US-09", "hinweis",
                f"Geschäftspartner {ctx.kontotext(partner)}: {top_n}/{n} "
                f"Buchungen mit '{top_sig}', Abweichler: "
                f"{'; '.join(details[:4])}.",
                "Abweichende steuerliche Behandlung desselben Partners "
                "klären (Schlüsselfehler, geänderter Sachverhalt).",
                konto=partner))
    return out


def us_10_vst_ohne_beleg(ctx: Kontext) -> list[Befund]:
    vst = [b for b in ctx.buchungen
           if b.bu and (ctx.plan.steuer(b) or ("", 0, None))[0] == "VSt"]
    if not vst:
        return []
    ohne = [b for b in vst if not b.belegfeld1.strip()]
    out = []
    quote = len(ohne) / len(vst)
    if quote > float(ctx.param["belegfeld_quote_warn"]):
        out.append(_b(ctx, "US-10", "hinweis",
            f"{len(ohne)} von {len(vst)} Vorsteuerbuchungen ({quote:.0%}) "
            "ohne Belegnummer.",
            "Vorsteuerabzug setzt Rechnung voraus (§ 15 Abs. 1 UStG i. V. m. "
            "§§ 14, 14a UStG); Belegzuordnung nachholen."))
    else:
        for b in sorted(ohne, key=lambda b: -b.umsatz)[:3]:
            if b.umsatz < Decimal(str(ctx.param["runde_min_eur"])):
                continue
            out.append(_b(ctx, "US-10", "hinweis",
                f"Vorsteuerbuchung {eur(b.umsatz)} EUR ohne Belegnummer.",
                "Rechnung zuordnen (§ 15 UStG).",
                konto=b.konto, gegenkonto=b.gegenkonto, datum=b.belegdatum,
                betrag=b.umsatz, buchungstext=b.buchungstext, quelle=_q(b)))
    return out


# ------------------------------------------------- Kreditoren (KR-01)

def kr_01_kreditor_belegnummer(ctx: Kontext) -> list[Befund]:
    gruppen: dict[tuple[int, str], list] = defaultdict(list)
    for b in ctx.buchungen:
        if not b.belegfeld1.strip() or ctx.ist_eb(b):
            continue
        kreditor = b.konto if ctx.plan.ist_kreditor(b.konto) else (
            b.gegenkonto if ctx.plan.ist_kreditor(b.gegenkonto) else None)
        if kreditor is None:
            continue
        sachseite = b.gegenkonto if kreditor == b.konto else b.konto
        if not (ctx.plan.ist_guv(sachseite) or ctx.plan.ist_av(sachseite)):
            continue  # nur Rechnungsbuchungen, keine Zahlungen
        gruppen[(kreditor, b.belegfeld1.strip())].append(b)
    out, uebrig = [], 0
    limit = _limit(ctx)
    for (kreditor, beleg), bs in sorted(gruppen.items()):
        betraege = {b.umsatz for b in bs}
        daten = {b.belegdatum for b in bs}
        if len(bs) < 2 or (len(betraege) == 1 and len(daten) == 1):
            continue  # Splitbuchung derselben Rechnung
        if len(betraege) == 1:
            continue  # identische Beträge: deckt ST-01 (Doppelbuchung) ab
        if len(out) >= limit:
            uebrig += 1
            continue
        details = "; ".join(
            f"{(b.belegdatum and f'{b.belegdatum:%d.%m.%Y}') or '?'} über "
            f"{eur(b.umsatz)} EUR" for b in bs[:4])
        out.append(_b(ctx, "KR-01", "mittel",
            f"Belegnummer '{beleg}' beim Kreditor {ctx.kontotext(kreditor)} "
            f"mehrfach mit abweichenden Beträgen gebucht: {details}.",
            "Rechnungsnummer klären: Teil-/Korrekturrechnung oder "
            "Erfassungsfehler (Doppelzahlungsrisiko).",
            konto=kreditor, datum=bs[0].belegdatum,
            betrag=sum((b.umsatz for b in bs), Decimal(0)),
            beleg=beleg, quelle=_q(bs[0])))
    _rest(ctx, out, "KR-01", uebrig, "Belegnummern-Dubletten")
    return out


# ------------------------------------------------- OPOS (OP-05/06/07)

def op_05_opos_abgleich(ctx: Kontext) -> list[Befund]:
    if ctx.opos is None:
        ctx.skip("OP-05", "erfordert OPOS-Liste (--opos)")
        return []
    toleranz = Decimal(str(ctx.param["opos_abgleich_toleranz"]))
    summen: dict[int, Decimal] = defaultdict(Decimal)
    for p in ctx.opos:
        summen[p.konto] += p.betrag
    out = []
    for konto in sorted(summen):
        erwartet = summen[konto] if ctx.plan.ist_debitor(konto) else -summen[konto]
        ist = ctx.saldo.get(konto, Decimal(0))
        diff = ist - erwartet
        if abs(diff) > toleranz:
            out.append(_b(ctx, "OP-05", "mittel",
                f"Konto {ctx.kontotext(konto)}: Saldo laut Stapel {eur(ist)} "
                f"EUR, laut OPOS-Liste {eur(erwartet)} EUR "
                f"(Differenz {eur(diff)} EUR).",
                "Nebenbuch abstimmen: Verrechnungen, Gutschriften oder nicht "
                "gepflegte OPOS-Posten klären.", konto=konto, betrag=diff))
    ohne_opos = [k for k in ctx.saldo
                 if ctx.plan.ist_personenkonto(k) and k not in summen
                 and abs(ctx.saldo[k]) > ctx.bagatelle]
    if ohne_opos:
        liste = ", ".join(str(k) for k in sorted(ohne_opos)[:10])
        out.append(_b(ctx, "OP-05", "hinweis",
            f"{len(ohne_opos)} Personenkonten mit Saldo ohne OPOS-Posten: "
            f"{liste}{' …' if len(ohne_opos) > 10 else ''}.",
            "OPOS-Liste auf Vollständigkeit prüfen."))
    return out


def op_06_alte_kleinstposten(ctx: Kontext) -> list[Befund]:
    if ctx.opos is None:
        ctx.skip("OP-06", "erfordert OPOS-Liste (--opos)")
        return []
    if ctx.datum_bis is None:
        ctx.skip("OP-06", "erfordert Stichtag (Header-Zeitraum)")
        return []
    grenze = ctx.datum_bis - timedelta(days=int(ctx.param["opos_alt_tage"]))
    kleinst = Decimal(str(ctx.param["opos_kleinst_eur"]))
    out, uebrig = [], 0
    limit = _limit(ctx)
    for p in ctx.opos:
        datum = p.faellig or p.belegdatum
        if not datum or datum >= grenze:
            continue
        if p.betrag < 0:
            art = "Alte Gutschrift"
            empf = ("Gutschrift verrechnen bzw. auszahlen; Ursache "
                    "dokumentieren.")
        elif 0 < p.betrag < kleinst:
            art = "Alter Kleinstposten"
            empf = "Ausbuchung/Bereinigung prüfen (OPOS-Hygiene)."
        else:
            continue
        if len(out) >= limit:
            uebrig += 1
            continue
        out.append(_b(ctx, "OP-06", "hinweis",
            f"{art} {ctx.kontotext(p.konto)}: {eur(p.betrag)} EUR, "
            f"fällig/belegdatiert {datum:%d.%m.%Y}.",
            empf, konto=p.konto, datum=datum, betrag=p.betrag, beleg=p.beleg))
    _rest(ctx, out, "OP-06", uebrig, "Altposten")
    return out


def op_07_konzentration(ctx: Kontext) -> list[Befund]:
    volumen: dict[int, Decimal] = {k: ctx.soll[k] for k in ctx.soll
                                   if ctx.plan.ist_debitor(k)}
    gesamt = sum(volumen.values(), Decimal(0))
    if gesamt <= 0 or len(volumen) < 2:
        return []
    konto, top = max(volumen.items(), key=lambda e: e[1])
    anteil = float(top / gesamt)
    if anteil > float(ctx.param["konzentration_warn"]):
        return [_b(ctx, "OP-07", "hinweis",
            f"Debitor {ctx.kontotext(konto)} vereint {anteil:.0%} des "
            f"Forderungsvolumens ({eur(top)} von {eur(gesamt)} EUR).",
            "Konzentrations-/Ausfallrisiko würdigen (Anhang-/"
            "Lageberichtsrelevanz, EWB-Überlegung).",
            konto=konto, betrag=top)]
    return []


# --------------------------------------------- Bilanz sonstige (BL-01..04)

def bl_01_rap(ctx: Kontext) -> list[Befund]:
    out = []
    rap_bewegt = False
    for k in ctx.konten_in("rap"):
        unterjaehrig = [e for e in ctx.bewegungen[k] if not ctx.ist_eb(e[3])]
        if unterjaehrig:
            rap_bewegt = True
            continue
        if abs(ctx.saldo[k]) > ctx.bagatelle:
            out.append(_b(ctx, "BL-01", "hinweis",
                f"RAP-Konto {ctx.kontotext(k)} mit Bestand {eur(ctx.saldo[k])} "
                "EUR ohne jede unterjährige Bewegung (Vorjahres-RAP nicht "
                "aufgelöst?).",
                "Auflösung bzw. Neubildung der Abgrenzung prüfen "
                "(§ 250 HGB).", konto=k, betrag=ctx.saldo[k]))
    indikator = Decimal(str(ctx.param["rap_indikator_min_eur"]))
    typisch = sum((ctx.saldo_netto[k] for k in ctx.anzahl
                   if ctx.plan.in_gruppe(k, "vst_unueblich")
                   and ctx.plan.ist_guv(k)), Decimal(0))
    if not rap_bewegt and typisch >= indikator:
        out.append(_b(ctx, "BL-01", "hinweis",
            f"Abgrenzungstypische Aufwendungen (u. a. Versicherungen/"
            f"Beiträge {eur(typisch)} EUR), aber keine unterjährige "
            "RAP-Bewegung.",
            "Prüfen, ob Zahlungen über den Stichtag hinaus abzugrenzen "
            "sind (§ 250 HGB).", betrag=typisch))
    return out


def bl_02_rueckstellungen(ctx: Kontext) -> list[Befund]:
    out = []
    for k in ctx.konten_in("rueckstellungen"):
        unterjaehrig = [e for e in ctx.bewegungen[k] if not ctx.ist_eb(e[3])]
        if not unterjaehrig and abs(ctx.saldo[k]) > ctx.bagatelle:
            out.append(_b(ctx, "BL-02", "hinweis",
                f"Rückstellungskonto {ctx.kontotext(k)} mit Bestand "
                f"{eur(ctx.saldo[k])} EUR ohne Verbrauch/Auflösung/Zuführung.",
                "Bewertung zum Stichtag prüfen (§ 249, § 253 Abs. 1 HGB): "
                "Verbrauch, Auflösung oder Anpassung erforderlich?",
                konto=k, betrag=ctx.saldo[k]))
    return out


def bl_03_darlehen_ohne_zins(ctx: Kontext) -> list[Befund]:
    bestand = sum((abs(ctx.saldo[k]) for k in ctx.konten_in("darlehen")), Decimal(0))
    if bestand < Decimal(str(ctx.param["darlehen_min_eur"])):
        return []
    zins = sum((ctx.soll[k] for k in ctx.anzahl
                if ctx.plan.in_gruppe(k, "zinsaufwand")), Decimal(0))
    if zins == 0:
        return [_b(ctx, "BL-03", "hinweis",
            f"Darlehensbestand {eur(bestand)} EUR ohne gebuchten Zinsaufwand.",
            "Zinsabgrenzung/Zinsbuchungen prüfen (fehlende Aufwandsperiodisierung).",
            betrag=bestand)]
    return []


def bl_04_ek_direktbuchungen(ctx: Kontext) -> list[Befund]:
    if ctx.datum_bis is None:
        return []
    abschluss_ab = ctx.datum_bis - timedelta(days=int(ctx.param["wj_ende_fenster_tage"]))
    je_konto: dict[int, list] = defaultdict(list)
    for k in ctx.konten_in("eigenkapital"):
        for d, _z, w, b in ctx.bewegungen[k]:
            if ctx.ist_eb(b) or (d and d > abschluss_ab):
                continue  # EB und Abschlussbuchungen sind üblich
            je_konto[k].append((d, w, b))
    out = []
    for k, eintraege in je_konto.items():
        summe = sum((abs(w) for _d, w, _b_ in eintraege), Decimal(0))
        d0, _w0, b0 = eintraege[0]
        out.append(_b(ctx, "BL-04", "hinweis",
            f"{len(eintraege)} unterjährige Direktbuchung(en) auf "
            f"Eigenkapitalkonto {ctx.kontotext(k)} (Summe {eur(summe)} EUR).",
            "Kapitalbewegungen außerhalb von EB/Ergebnisverwendung klären "
            "(Entnahme/Einlage/Umgliederung).",
            konto=k, datum=d0, betrag=summe,
            buchungstext=b0.buchungstext, quelle=_q(b0)))
    return out


# --------------------------------------------- GuV-Plausibilität (GV-01..03)

def gv_01_monatsspitzen(ctx: Kontext) -> list[Befund]:
    faktor = float(ctx.param["monatsspitze_faktor"])
    min_monate = int(ctx.param["monatsspitze_min_monate"])
    out = []
    for k in sorted(ctx.anzahl):
        if not ctx.plan.ist_guv(k) or ctx.plan.in_gruppe(k, "afa"):
            continue
        monate: dict[str, Decimal] = defaultdict(Decimal)
        max_einzel: dict[str, Decimal] = defaultdict(Decimal)
        for d, _z, w, b in ctx.bewegungen[k]:
            if d is None or ctx.ist_eb(b):
                continue
            schluessel = f"{d.year}-{d.month:02d}"
            monate[schluessel] += abs(w)
            max_einzel[schluessel] = max(max_einzel[schluessel], abs(w))
        if len(monate) < min_monate:
            continue
        werte = sorted(monate.values())
        med = werte[len(werte) // 2]
        spitze_monat, spitze = max(monate.items(), key=lambda e: e[1])
        if med > 0 and float(spitze / med) > faktor and spitze >= 1000:
            if max_einzel[spitze_monat] / spitze > Decimal("0.8"):
                continue  # Einzelausreißer: deckt ST-02 ab
            out.append(_b(ctx, "GV-01", "hinweis",
                f"Konto {ctx.kontotext(k)}: Monat {spitze_monat} mit "
                f"{eur(spitze)} EUR deutlich über dem Medianmonat "
                f"({eur(med)} EUR).",
                "Monatshäufung klären: Nachbuchungen, Periodenverschiebung "
                "oder Sondereffekt.", konto=k, betrag=spitze, llm=True))
    return out


def gv_02_gegenlauf(ctx: Kontext) -> list[Befund]:
    dominanz = float(ctx.param["gegenlauf_dominanz"])
    minimum = Decimal(str(ctx.param["gegenlauf_min_eur"]))
    out = []
    for k in sorted(ctx.anzahl):
        if not ctx.plan.ist_guv(k):
            continue
        bew = [(d, w, b) for d, _z, w, b in ctx.bewegungen[k]
               if not ctx.ist_eb(b) and not b.storno]
        if len(bew) < 10:
            continue
        soll_n = sum(1 for _d, w, _b_ in bew if w > 0)
        haupt = 1 if soll_n >= len(bew) - soll_n else -1
        if max(soll_n, len(bew) - soll_n) / len(bew) < dominanz:
            continue
        treffer = 0
        for d, w, b in bew:
            if w * haupt < 0 and abs(w) >= minimum:
                treffer += 1
                if treffer > 2:
                    break
                out.append(_b(ctx, "GV-02", "hinweis",
                    f"Gegenläufige Buchung {eur(abs(w))} EUR auf "
                    f"richtungsstabilem Konto {ctx.kontotext(k)} "
                    f"({'Soll' if haupt > 0 else 'Haben'}-dominant).",
                    "Korrektur/Storno/Umbuchung prüfen (Erlösminderung auf "
                    "Aufwandskonto o. ä.).",
                    konto=k, datum=d, betrag=abs(w), beleg=b.belegfeld1,
                    buchungstext=b.buchungstext, quelle=_q(b), llm=True))
    return out


def gv_03_seltene_kombination(ctx: Kontext) -> list[Befund]:
    min_n = int(ctx.param["seltene_kombi_min_konto_n"])
    minimum = Decimal(str(ctx.param["llm_kandidat_min_eur"]))
    kombis: dict[int, Counter] = defaultdict(Counter)
    beispiel: dict[tuple[int, int], object] = {}
    for b in ctx.buchungen:
        if ctx.ist_eb(b):
            continue
        guv = b.konto if ctx.plan.ist_guv(b.konto) else (
            b.gegenkonto if ctx.plan.ist_guv(b.gegenkonto) else None)
        if guv is None:
            continue
        gegen = b.gegenkonto if guv == b.konto else b.konto
        kombis[guv][gegen] += 1
        beispiel.setdefault((guv, gegen), b)
    treffer = []
    for k, zaehler in sorted(kombis.items()):
        n = sum(zaehler.values())
        if n < min_n:
            continue
        for gegen, anz in zaehler.items():
            if anz != 1:
                continue
            b = beispiel[(k, gegen)]
            if b.umsatz < minimum:
                continue
            treffer.append(_b(ctx, "GV-03", "hinweis",
                f"Einmalige Kontierung {ctx.kontotext(k)} an "
                f"{ctx.kontotext(gegen)} ({eur(b.umsatz)} EUR) bei sonst "
                f"{n - 1} anders kontierten Buchungen.",
                "Untypischen Buchungsweg prüfen (Fehlkontierung, "
                "Sondervorgang).",
                konto=k, gegenkonto=gegen, datum=b.belegdatum,
                betrag=b.umsatz, beleg=b.belegfeld1,
                buchungstext=b.buchungstext, quelle=_q(b), llm=True))
    limit = _limit(ctx)
    out = treffer[:limit]
    _rest(ctx, out, "GV-03", max(0, len(treffer) - limit), "Einmal-Kontierungen")
    return out


# ---------------------------------------------------- Ertragsteuer (ET)

def et_01_geschenke(ctx: Kontext) -> list[Befund]:
    jahr = ctx.datum_von.year if ctx.datum_von else 9999
    grenze = Decimal(str(ctx.param["geschenke_grenze_ab_2024"] if jahr >= 2024
                         else ctx.param["geschenke_grenze_bis_2023"]))
    out = []
    for k in ctx.konten_in("geschenke_abz"):
        for d, _z, w, b in ctx.bewegungen[k]:
            if w <= 0 or ctx.ist_eb(b):
                continue
            netto = ctx.plan.netto(b)
            if netto > grenze:
                out.append(_b(ctx, "ET-01", "mittel",
                    f"Geschenk {eur(netto)} EUR netto auf Abziehbar-Konto "
                    f"{ctx.kontotext(k)} über der Grenze ({eur(grenze)} EUR "
                    f"je Empfänger/Jahr).",
                    "Umbuchung auf nicht abziehbar prüfen (§ 4 Abs. 5 Nr. 1 "
                    "EStG); Empfängeraufzeichnung § 4 Abs. 7 EStG; "
                    "Vorsteuerausschluss § 15 Abs. 1a UStG beachten.",
                    konto=k, datum=d, betrag=netto, beleg=b.belegfeld1,
                    buchungstext=b.buchungstext, quelle=_q(b)))
    return out


def et_02_textmuster(ctx: Kontext) -> list[Befund]:
    regeln = ctx.param.get("textmuster", [])
    if not regeln:
        ctx.skip("ET-02", "erfordert Konfiguration 'textmuster'")
        return []
    kompiliert = [(r["label"], re.compile(r["muster"], re.IGNORECASE),
                   r.get("erlaubt_gruppen", [])) for r in regeln]
    out = []
    for b in ctx.buchungen:
        if ctx.ist_eb(b) or not b.buchungstext:
            continue
        guv = b.konto if ctx.plan.ist_guv(b.konto) else (
            b.gegenkonto if ctx.plan.ist_guv(b.gegenkonto) else None)
        if guv is None:
            continue
        for label, muster, erlaubt in kompiliert:
            if not muster.search(b.buchungstext):
                continue
            if any(ctx.plan.in_gruppe(guv, g) for g in erlaubt):
                continue
            out.append(_b(ctx, "ET-02", "hinweis",
                f"Buchungstext deutet auf '{label}', gebucht auf "
                f"{ctx.kontotext(guv)} statt auf dem dafür vorgesehenen "
                "Kontenbereich.",
                "Steuerliche Behandlung prüfen (Abzugsverbote § 4 Abs. 5, "
                "5b EStG; getrennte Aufzeichnung § 4 Abs. 7 EStG).",
                konto=guv, datum=b.belegdatum, betrag=b.umsatz,
                beleg=b.belegfeld1, buchungstext=b.buchungstext,
                quelle=_q(b), llm=True))
            break
    limit = _limit(ctx)
    gekuerzt = out[:limit]
    _rest(ctx, gekuerzt, "ET-02", max(0, len(out) - limit), "Textmuster-Treffer")
    return gekuerzt


# ---------------------------------------------------------- Cut-off (CO)

def co_01_periodenende(ctx: Kontext) -> list[Befund]:
    if ctx.datum_bis is None:
        ctx.skip("CO-01", "erfordert Stichtag (Header-Zeitraum)")
        return []
    ab = ctx.datum_bis - timedelta(days=int(ctx.param["wj_ende_fenster_tage"]))
    minimum = Decimal(str(ctx.param["cutoff_min_eur"]))
    serien = Counter((b.umsatz, b.konto, b.gegenkonto)
                     for b in ctx.buchungen if not ctx.ist_eb(b))
    out, uebrig = [], 0
    limit = _limit(ctx)
    for b in ctx.buchungen:
        if ctx.ist_eb(b) or b.belegdatum is None or b.belegdatum <= ab:
            continue
        if serien[(b.umsatz, b.konto, b.gegenkonto)] >= 4:
            continue  # Dauerbuchungen (Monatsgehälter etc.) sind kein Cut-off-Indiz
        guv = b.konto if ctx.plan.ist_guv(b.konto) else (
            b.gegenkonto if ctx.plan.ist_guv(b.gegenkonto) else None)
        if guv is None or ctx.plan.in_gruppe(guv, "afa"):
            continue  # planmäßige Abschlussbuchungen ausnehmen
        if b.umsatz < minimum:
            continue
        if len(out) >= limit:
            uebrig += 1
            continue
        art = "Erlös" if ctx.plan.in_gruppe(guv, "ertrag") else "Aufwand"
        out.append(_b(ctx, "CO-01", "hinweis",
            f"Wesentliche {art}sbuchung {eur(b.umsatz)} EUR am "
            f"{b.belegdatum:%d.%m.%Y} (letzte {ctx.param['wj_ende_fenster_tage']} "
            "Tage des Zeitraums).",
            "Periodenzugehörigkeit prüfen (Cut-off: Leistungsdatum, "
            "Abgrenzung, ggf. Stornierung im Folgejahr).",
            konto=guv, datum=b.belegdatum, betrag=b.umsatz,
            beleg=b.belegfeld1, buchungstext=b.buchungstext, quelle=_q(b),
            llm=True))
    _rest(ctx, out, "CO-01", uebrig, "Periodenend-Buchungen")
    return out


# ---------------------------------------------------- Gesellschafter (GS)

def gs_01_gesellschafterkonten(ctx: Kontext) -> list[Befund]:
    minimum = Decimal(str(ctx.param["llm_kandidat_min_eur"]))
    out = []
    for k in ctx.konten_in("gesellschafter"):
        bew = [(d, w, b) for d, _z, w, b in ctx.bewegungen[k] if not ctx.ist_eb(b)]
        if not bew:
            continue
        summe = sum((abs(w) for _d, w, _b_ in bew), Decimal(0))
        out.append(_b(ctx, "GS-01", "hinweis",
            f"Gesellschafterkonto {ctx.kontotext(k)}: {len(bew)} Bewegung(en), "
            f"Volumen {eur(summe)} EUR, Saldo {eur(ctx.saldo[k])} EUR.",
            "Fremdvergleich und Veranlassung dokumentieren (Verzinsung, "
            "Verträge; vGA-/Entnahme-Risiken würdigen).",
            konto=k, betrag=ctx.saldo[k]))
        for d, w, b in sorted(bew, key=lambda e: -abs(e[1]))[:3]:
            if abs(w) >= minimum:
                out.append(_b(ctx, "GS-01", "hinweis",
                    f"Gesellschafter-Einzelvorgang {eur(abs(w))} EUR auf "
                    f"{ctx.kontotext(k)}.",
                    "Vertragsgrundlage/Fremdüblichkeit prüfen.",
                    konto=k, gegenkonto=b.gegenkonto if b.konto == k else b.konto,
                    datum=d, betrag=abs(w), beleg=b.belegfeld1,
                    buchungstext=b.buchungstext, quelle=_q(b), llm=True))
    return out


# ---------------------------------------------------- Fraud (FR-01..04)

def fr_01_stornoquote(ctx: Kontext) -> list[Befund]:
    basis = [b for b in ctx.buchungen if not ctx.ist_eb(b)]
    if len(basis) < int(ctx.param["storno_min_n"]):
        ctx.skip("FR-01", f"zu wenige Buchungen ({len(basis)} < "
                          f"{ctx.param['storno_min_n']})")
        return []
    stornos = [b for b in basis if b.storno]
    out = []
    quote = len(stornos) / len(basis)
    if quote > float(ctx.param["storno_quote_warn"]):
        out.append(_b(ctx, "FR-01", "hinweis",
            f"Stornoquote {quote:.1%} ({len(stornos)} von {len(basis)} "
            "Buchungen) über dem Schwellwert.",
            "Stornogründe stichprobenhaft prüfen (Erfassungsqualität, "
            "nachträgliche Ergebnissteuerung)."))
    wiederholt = Counter((b.umsatz, b.konto, b.gegenkonto) for b in stornos)
    for (betrag, konto, gegen), anz in wiederholt.items():
        if anz >= 2:
            out.append(_b(ctx, "FR-01", "hinweis",
                f"Sachverhalt {eur(betrag)} EUR ({konto} an {gegen}) wurde "
                f"{anz}-mal storniert.",
                "Mehrfachstorno und Wiedereinbuchung klären.",
                konto=konto, gegenkonto=gegen, betrag=betrag))
    return out


def fr_02_einmal_kreditoren(ctx: Kontext) -> list[Befund]:
    minimum = Decimal(str(ctx.param["einmal_kreditor_min_eur"]))
    max_buchungen = int(ctx.param["einmal_kreditor_max_buchungen"])
    out = []
    for k in sorted(ctx.anzahl):
        if not ctx.plan.ist_kreditor(k):
            continue
        if ctx.anzahl[k] > max_buchungen:
            continue
        volumen = max(ctx.soll[k], ctx.haben[k])
        if volumen >= minimum:
            beispiel = ctx.bewegungen[k][0][3]
            out.append(_b(ctx, "FR-02", "hinweis",
                f"Kreditor {ctx.kontotext(k)} mit nur {ctx.anzahl[k]} "
                f"Buchung(en), aber Volumen {eur(volumen)} EUR.",
                "Einmal-Lieferanten mit hohem Volumen verifizieren "
                "(Leistungsnachweis, Stammdaten, Freigabeweg).",
                konto=k, betrag=volumen,
                buchungstext=beispiel.buchungstext,
                quelle=_q(beispiel), llm=True))
    return out


def fr_03_freigabegrenzen(ctx: Kontext) -> list[Befund]:
    grenzen = ctx.param.get("freigabegrenzen", [])
    if not grenzen:
        ctx.skip("FR-03", "erfordert Konfiguration 'freigabegrenzen'")
        return []
    band = Decimal(str(ctx.param["splitting_band"]))
    out = []
    for grenze_roh in grenzen:
        grenze = Decimal(str(grenze_roh))
        treffer = [b for b in ctx.buchungen
                   if not ctx.ist_eb(b) and band * grenze <= b.umsatz < grenze]
        if len(treffer) >= 3:
            out.append(_b(ctx, "FR-03", "hinweis",
                f"{len(treffer)} Buchungen knapp unter der Freigabegrenze "
                f"{eur(grenze)} EUR.",
                "Häufung unterhalb von Freigabe-/Genehmigungsgrenzen "
                "stichprobenhaft prüfen.", betrag=grenze))
    return out


def fr_04_endziffern(ctx: Kontext) -> list[Befund]:
    werte = [b.umsatz for b in ctx.buchungen
             if not ctx.ist_eb(b) and b.umsatz >= 10
             and (ctx.plan.ist_guv(b.konto) or ctx.plan.ist_guv(b.gegenkonto))]
    min_n = int(ctx.param["endziffern_min_n"])
    if len(werte) < min_n:
        ctx.skip("FR-04", f"zu wenige GuV-Buchungen ({len(werte)} < {min_n})")
        return []
    glatt = sum(1 for w in werte if int(w * 100) % 100 == 0)
    quote = glatt / len(werte)
    if quote > float(ctx.param["endziffern_00_warn"]):
        return [_b(ctx, "FR-04", "hinweis",
            f"{quote:.0%} der GuV-Buchungen ohne Centbetrag (n={len(werte)}); "
            "Screening-Indiz für Schätz-/Pauschalbuchungen.",
            "Nur Risikosignal, kein Fehlernachweis: mit Preisstruktur des "
            "Geschäfts abgleichen.")]
    return []


# ---------------------------------------------------- Stammdaten (SD)

def sd_01_namensdubletten(ctx: Kontext) -> list[Befund]:
    if not ctx.namen:
        ctx.skip("SD-01", "erfordert Kontenbeschriftungen (EXTF Kat. 20)")
        return []
    gruppen: dict[str, list[int]] = defaultdict(list)
    for konto, name in ctx.namen.items():
        if ctx.plan.ist_personenkonto(konto) and len(name.strip()) >= 3:
            gruppen[name.strip().lower()].append(konto)
    out = []
    for name, konten in sorted(gruppen.items()):
        if len(konten) > 1:
            out.append(_b(ctx, "SD-01", "hinweis",
                f"Personenkonten {', '.join(map(str, sorted(konten)))} mit "
                f"identischer Bezeichnung '{ctx.namen[konten[0]]}'.",
                "Stammsatz-Dubletten bereinigen (Doppelzahlungs-/"
                "OPOS-Splitterrisiko)."))
    return out[:10]


ALLE_ERWEITERT = [
    dv_01_nullwerte, dv_02_eb_auf_guv, dv_03_konten_ohne_namen,
    sb_09_kassenbewegung_ausreisser, sb_10_glatte_barbewegungen,
    us_08_automatik_konflikt, us_09_schluesselwechsel_partner,
    us_10_vst_ohne_beleg,
    kr_01_kreditor_belegnummer,
    op_05_opos_abgleich, op_06_alte_kleinstposten, op_07_konzentration,
    bl_01_rap, bl_02_rueckstellungen, bl_03_darlehen_ohne_zins,
    bl_04_ek_direktbuchungen,
    gv_01_monatsspitzen, gv_02_gegenlauf, gv_03_seltene_kombination,
    et_01_geschenke, et_02_textmuster,
    co_01_periodenende,
    gs_01_gesellschafterkonten,
    fr_01_stornoquote, fr_02_einmal_kreditoren, fr_03_freigabegrenzen,
    fr_04_endziffern,
    sd_01_namensdubletten,
]
