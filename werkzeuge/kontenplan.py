"""Kontenrahmen-Logik: SKR-Erkennung, Kontengruppen, Steuerableitung.

Alle Kontenbereiche kommen aus konten_config.json (kanonisch 4-stellig)
und werden auf die tatsaechliche Sachkontenlaenge skaliert.
"""

from __future__ import annotations

from decimal import Decimal

from datev_parser import Buchung


class Kontenplan:
    def __init__(self, cfg: dict, skr: str, sachkontenlaenge: int = 4):
        self.skr = skr
        self.skl = max(4, sachkontenlaenge)
        self.faktor = 10 ** (self.skl - 4)
        self.deb_von = 10 ** self.skl
        self.deb_bis = 7 * 10 ** self.skl - 1
        self.kred_bis = 10 ** (self.skl + 1) - 1
        self.steuerschluessel = {
            k: (v[0], int(v[1])) for k, v in cfg["steuerschluessel"].items()
            if not k.startswith("_")
        }
        roh = cfg["skr03" if skr == "03" else "skr04"]
        self.gruppen: dict[str, list[tuple[int, int]]] = {}
        for name, bereiche in roh.items():
            if name.startswith("_") or name == "automatik":
                continue
            self.gruppen[name] = [self._skaliere(a, b) for a, b in bereiche]
        self.automatik: list[tuple[int, int, str, int]] = []
        for schluessel, (art, satz) in roh.get("automatik", {}).items():
            a, b = (int(x) for x in schluessel.split(","))
            von, bis = self._skaliere(a, b)
            self.automatik.append((von, bis, art, int(satz)))

    def _skaliere(self, a: int, b: int) -> tuple[int, int]:
        return a * self.faktor, b * self.faktor + self.faktor - 1

    def in_gruppe(self, konto: int, name: str) -> bool:
        return any(a <= konto <= b for a, b in self.gruppen.get(name, []))

    def gruppen_von(self, konto: int) -> list[str]:
        return [g for g in self.gruppen if self.in_gruppe(konto, g)]

    def ist_sachkonto(self, konto: int) -> bool:
        return 0 < konto < self.deb_von

    def ist_debitor(self, konto: int) -> bool:
        return self.deb_von <= konto <= self.deb_bis

    def ist_kreditor(self, konto: int) -> bool:
        return self.deb_bis < konto <= self.kred_bis

    def ist_personenkonto(self, konto: int) -> bool:
        return self.ist_debitor(konto) or self.ist_kreditor(konto)

    def ist_guv(self, konto: int) -> bool:
        if not self.ist_sachkonto(konto):
            return False
        norm = konto // self.faktor
        if self.skr == "03":
            return 2000 <= norm <= 4999 or 8000 <= norm <= 8999
        return 4000 <= norm <= 7999

    def ist_av(self, konto: int) -> bool:
        return (self.in_gruppe(konto, "av_abnutzbar")
                or self.in_gruppe(konto, "av_nicht_abnutzbar")
                or self.in_gruppe(konto, "gwg"))

    def ist_debitorisch(self, konto: int) -> bool:
        return self.ist_debitor(konto) or self.in_gruppe(konto, "forderungen_sammel")

    def _automatik_satz(self, konto: int) -> tuple[str, int] | None:
        for von, bis, art, satz in self.automatik:
            if von <= konto <= bis:
                return art, satz
        return None

    def steuer(self, b: Buchung) -> tuple[str, int, str | None] | None:
        """Liefert (Art, Satz, Steuerseite) oder None.

        Steuerseite = die Buchungsseite (konto/gegenkonto), der der
        Steueranteil sachlich zuzurechnen ist (GuV- bzw. AV-Seite).
        BU-Schluessel hat Vorrang; ohne Schluessel greifen Automatikkonten.
        """
        art_satz: tuple[str, int] | None = None
        seite: str | None = None
        if b.bu:
            ziffer = b.bu[-1]
            eintrag = self.steuerschluessel.get(ziffer)
            if not eintrag or eintrag[1] == 0:
                return None
            art_satz = eintrag
        else:
            for s, konto in (("konto", b.konto), ("gegenkonto", b.gegenkonto)):
                treffer = self._automatik_satz(konto)
                if treffer:
                    art_satz, seite = treffer, s
                    break
            if art_satz is None:
                return None
        if seite is None:
            k_sach = self.ist_guv(b.konto) or self.ist_av(b.konto)
            g_sach = self.ist_guv(b.gegenkonto) or self.ist_av(b.gegenkonto)
            if k_sach and not g_sach:
                seite = "konto"
            elif g_sach and not k_sach:
                seite = "gegenkonto"
            elif k_sach and g_sach:
                seite = "konto"
        return art_satz[0], art_satz[1], seite

    def netto(self, b: Buchung) -> Decimal:
        """Nettobetrag der Buchung (Bruttoumsatz um Steueranteil bereinigt)."""
        st = self.steuer(b)
        if not st or st[1] == 0:
            return b.umsatz
        return (b.umsatz * 100 / (100 + st[1])).quantize(Decimal("0.01"))


def erkenne_skr(buchungen: list[Buchung], sachkontenlaenge: int) -> tuple[str, str]:
    """Heuristik: SKR03 vs. SKR04 anhand exklusiver Kontenklassen.

    SKR03: Klassen 5/6 frei, Erloese in 8, Kasse 1000.
    SKR04: Klasse 8 frei, Aufwand in 5/6, Kasse 1600.
    """
    f = 10 ** (max(4, sachkontenlaenge) - 4)
    grenze = 10 ** max(4, sachkontenlaenge)
    s03 = s04 = 0
    for b in buchungen:
        for k in (b.konto, b.gegenkonto):
            if k >= grenze:
                continue
            norm = k // f
            if 8000 <= norm <= 8999 or 1000 <= norm <= 1009:
                s03 += 1
            if 5000 <= norm <= 6999 or 1600 <= norm <= 1609:
                s04 += 1
    skr = "03" if s03 >= s04 else "04"
    return skr, f"SKR{skr} automatisch erkannt (Indizien SKR03: {s03}, SKR04: {s04})"
