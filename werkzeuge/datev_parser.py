"""Parser fuer Dateien im DATEV-Format (EXTF/DTVF).

Unterstuetzt: Buchungsstapel (Formatkategorie 21) und Kontenbeschriftungen
(Formatkategorie 20). Zusaetzlich tolerante Leser fuer frei exportierte
SuSa- und OPOS-CSV-Dateien.

Formathinweise Buchungsstapel:
- Zeile 1: Metadaten-Header (WJ-Beginn, Sachkontenlaenge, Zeitraum, ...)
- Zeile 2: Spaltenueberschriften, Zuordnung erfolgt ueber Spaltennamen
- Belegdatum im Format TTMM (ohne Jahr); das Jahr wird aus dem
  Header-Zeitraum abgeleitet
- Umsatz stets positiv, Richtung ueber Soll/Haben-Kennzeichen (bezogen
  auf das Konto in Feld "Konto")
- BU-Schluessel: letzte Ziffer = Steuerschluessel, fuehrende "2" =
  Generalumkehr (Storno)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


@dataclass
class StapelInfo:
    quelle: str
    kennzeichen: str = ""
    kategorie: int = 0
    berater: str = ""
    mandant: str = ""
    wj_beginn: date | None = None
    sachkontenlaenge: int = 4
    datum_von: date | None = None
    datum_bis: date | None = None
    bezeichnung: str = ""


@dataclass
class Buchung:
    umsatz: Decimal
    sh: str
    konto: int
    gegenkonto: int
    bu: str
    storno: bool
    belegdatum: date | None
    belegfeld1: str
    buchungstext: str
    kost1: str
    zeile: int
    quelle: str


def _lies_text(pfad: str | Path) -> str:
    roh = Path(pfad).read_bytes()
    if roh.startswith(b"\xef\xbb\xbf"):
        return roh.decode("utf-8-sig")
    try:
        return roh.decode("utf-8")
    except UnicodeDecodeError:
        return roh.decode("cp1252")


def _zeilen(pfad: str | Path) -> list[list[str]]:
    text = _lies_text(pfad)
    return list(csv.reader(text.splitlines(), delimiter=";", quotechar='"'))


def _norm(name: str) -> str:
    name = name.strip().strip('"').lower()
    for a, b in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "s")):
        name = name.replace(a, b)
    return "".join(c for c in name if c.isalnum())


def _dec(s: str) -> Decimal:
    return Decimal(s.strip().replace(".", "").replace(",", "."))


def _datum8(s: str) -> date | None:
    s = s.strip().strip('"')
    if len(s) == 8 and s.isdigit():
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except ValueError:
            return None
    return None


def lies_header(pfad: str | Path) -> StapelInfo:
    """Liest nur die Metadaten-Zeile (zur Format-Erkennung/Routing)."""
    felder = _zeilen(pfad)[0] if _zeilen(pfad) else []
    info = StapelInfo(quelle=str(pfad))
    if not felder:
        return info
    info.kennzeichen = felder[0].strip().strip('"')
    def _f(i: int) -> str:
        return felder[i].strip().strip('"') if len(felder) > i else ""
    try:
        info.kategorie = int(_f(2) or 0)
    except ValueError:
        info.kategorie = 0
    info.berater = _f(10)
    info.mandant = _f(11)
    info.wj_beginn = _datum8(_f(12))
    try:
        info.sachkontenlaenge = int(_f(13) or 4)
    except ValueError:
        info.sachkontenlaenge = 4
    info.datum_von = _datum8(_f(14))
    info.datum_bis = _datum8(_f(15))
    info.bezeichnung = _f(16)
    return info


def _belegdatum(roh: str, von: date | None, bis: date | None,
                wj: date | None) -> date | None:
    roh = roh.strip().strip('"')
    if not roh or not roh.isdigit() or len(roh) < 3:
        return None
    mm, tt = int(roh[-2:]), int(roh[:-2])
    jahre: list[int] = []
    for d in (von, bis, wj):
        if d and d.year not in jahre:
            jahre.append(d.year)
    if not jahre:
        jahre = [date.today().year]
    kandidaten = []
    for jahr in jahre:
        try:
            kandidaten.append(date(jahr, mm, tt))
        except ValueError:
            continue
    if not kandidaten:
        return None
    if von and bis:
        for k in kandidaten:
            if von <= k <= bis:
                return k
    return kandidaten[0]


# Spaltenname (normalisiert) -> internes Feld
_SPALTEN = {
    "umsatzohnesollhabenkz": "umsatz",
    "umsatz": "umsatz",
    "sollhabenkennzeichen": "sh",
    "konto": "konto",
    "gegenkontoohnebuschlussel": "gegenkonto",
    "gegenkonto": "gegenkonto",
    "buschlussel": "bu",
    "belegdatum": "belegdatum",
    "belegfeld1": "belegfeld1",
    "buchungstext": "buchungstext",
    "kost1kostenstelle": "kost1",
}


def lies_buchungsstapel(pfad: str | Path) -> tuple[StapelInfo, list[Buchung], list[str]]:
    zeilen = _zeilen(pfad)
    info = lies_header(pfad)
    warnungen: list[str] = []
    name = Path(pfad).name
    if len(zeilen) < 3:
        warnungen.append(f"{name}: Datei enthaelt keine Buchungszeilen")
        return info, [], warnungen

    idx: dict[str, int] = {}
    for i, spalte in enumerate(zeilen[1]):
        feld = _SPALTEN.get(_norm(spalte))
        if feld and feld not in idx:
            idx[feld] = i
    pflicht = {"umsatz", "sh", "konto", "gegenkonto", "belegdatum"}
    if not pflicht <= idx.keys():
        warnungen.append(f"{name}: Pflichtspalten fehlen ({pflicht - idx.keys()})")
        return info, [], warnungen

    def _wert(row: list[str], feld: str) -> str:
        i = idx.get(feld)
        return row[i].strip() if i is not None and i < len(row) else ""

    buchungen: list[Buchung] = []
    for nr, row in enumerate(zeilen[2:], start=3):
        if not row or not any(f.strip() for f in row):
            continue
        try:
            umsatz = _dec(_wert(row, "umsatz"))
        except (InvalidOperation, ValueError):
            warnungen.append(f"{name} Zeile {nr}: Umsatz nicht lesbar")
            continue
        sh = _wert(row, "sh").upper()
        if sh not in ("S", "H"):
            warnungen.append(f"{name} Zeile {nr}: Soll/Haben-Kennzeichen '{sh}' ungueltig")
            continue
        try:
            konto = int(_wert(row, "konto"))
            gegenkonto = int(_wert(row, "gegenkonto"))
        except ValueError:
            warnungen.append(f"{name} Zeile {nr}: Konto/Gegenkonto nicht lesbar")
            continue
        bu = _wert(row, "bu")
        storno = len(bu) >= 2 and bu[0] == "2"
        roh_datum = _wert(row, "belegdatum")
        belegdatum = _belegdatum(roh_datum, info.datum_von, info.datum_bis, info.wj_beginn)
        if belegdatum is None and roh_datum:
            warnungen.append(f"{name} Zeile {nr}: Belegdatum '{roh_datum}' ungueltig")
        buchungen.append(Buchung(
            umsatz=umsatz.copy_abs(), sh=sh, konto=konto, gegenkonto=gegenkonto,
            bu=bu, storno=storno, belegdatum=belegdatum,
            belegfeld1=_wert(row, "belegfeld1"), buchungstext=_wert(row, "buchungstext"),
            kost1=_wert(row, "kost1"), zeile=nr, quelle=name,
        ))
    return info, buchungen, warnungen


def lies_kontenbeschriftungen(pfad: str | Path) -> dict[int, str]:
    zeilen = _zeilen(pfad)
    if len(zeilen) < 3:
        return {}
    ik = ib = None
    for i, spalte in enumerate(zeilen[1]):
        n = _norm(spalte)
        if n == "konto" and ik is None:
            ik = i
        if n in ("kontenbeschriftung", "kontobeschriftung") and ib is None:
            ib = i
    if ik is None or ib is None:
        return {}
    namen: dict[int, str] = {}
    for row in zeilen[2:]:
        if len(row) <= max(ik, ib):
            continue
        try:
            namen[int(row[ik].strip())] = row[ib].strip().strip('"')
        except ValueError:
            continue
    return namen


def _finde_kopfzeile(zeilen: list[list[str]], muss: list[str]) -> tuple[int, dict[str, int]] | None:
    """Sucht in den ersten 10 Zeilen eine Kopfzeile, die alle Begriffe enthaelt."""
    for zi, row in enumerate(zeilen[:10]):
        norm = [_norm(z) for z in row]
        idx: dict[str, int] = {}
        for begriff in muss:
            for i, n in enumerate(norm):
                if begriff in n:
                    idx[begriff] = i
                    break
        if len(idx) == len(muss):
            return zi, idx
    return None


def lies_susa(pfad: str | Path) -> dict[int, Decimal]:
    """Toleranter SuSa-Leser: erwartet Spalten Konto und Saldo
    (alternativ Soll+Haben). Saldo-Konvention: Soll positiv."""
    zeilen = _zeilen(pfad)
    kopf = _finde_kopfzeile(zeilen, ["konto", "saldo"])
    modus = "saldo"
    if kopf is None:
        kopf = _finde_kopfzeile(zeilen, ["konto", "soll", "haben"])
        modus = "sollhaben"
    if kopf is None:
        return {}
    zi, idx = kopf
    salden: dict[int, Decimal] = {}
    for row in zeilen[zi + 1:]:
        try:
            konto = int(row[idx["konto"]].strip())
            if modus == "saldo":
                saldo = _dec(row[idx["saldo"]])
            else:
                saldo = _dec(row[idx["soll"]] or "0") - _dec(row[idx["haben"]] or "0")
            salden[konto] = salden.get(konto, Decimal(0)) + saldo
        except (ValueError, InvalidOperation, IndexError):
            continue
    return salden


@dataclass
class OposPosten:
    konto: int
    betrag: Decimal
    belegdatum: date | None
    faellig: date | None
    beleg: str


def _datum_frei(s: str) -> date | None:
    s = s.strip().strip('"')
    for trenner in (".", "-", "/"):
        teile = s.split(trenner)
        if len(teile) == 3:
            try:
                a, b, c = (int(t) for t in teile)
            except ValueError:
                return None
            try:
                return date(c, b, a) if c > 1900 else date(a, b, c)
            except ValueError:
                return None
    return _datum8(s)


def lies_opos(pfad: str | Path) -> list[OposPosten]:
    """Toleranter OPOS-Leser: Spalten Konto + Betrag (offen); optional
    Belegdatum/Rechnungsdatum, Faelligkeit, Belegnummer."""
    zeilen = _zeilen(pfad)
    kopf = _finde_kopfzeile(zeilen, ["konto", "betrag"])
    if kopf is None:
        return []
    zi, idx = kopf
    norm_kopf = [_norm(z) for z in zeilen[zi]]

    def _spalte(*begriffe: str) -> int | None:
        for begriff in begriffe:
            for i, n in enumerate(norm_kopf):
                if begriff in n:
                    return i
        return None

    i_datum = _spalte("belegdatum", "rechnungsdatum", "datum")
    i_faellig = _spalte("fallig")
    i_beleg = _spalte("belegnr", "belegfeld", "rechnungsnr", "beleg")
    posten: list[OposPosten] = []
    for row in zeilen[zi + 1:]:
        try:
            konto = int(row[idx["konto"]].strip())
            betrag = _dec(row[idx["betrag"]])
        except (ValueError, InvalidOperation, IndexError):
            continue
        def _g(i: int | None) -> str:
            return row[i] if i is not None and i < len(row) else ""
        posten.append(OposPosten(
            konto=konto, betrag=betrag,
            belegdatum=_datum_frei(_g(i_datum)),
            faellig=_datum_frei(_g(i_faellig)),
            beleg=_g(i_beleg).strip().strip('"'),
        ))
    return posten
