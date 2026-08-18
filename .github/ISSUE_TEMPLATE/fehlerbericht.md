---
name: Fehlerbericht
about: Ein Check meldet falsch, fehlt oder die Pipeline bricht ab
title: "[Fehler] "
labels: bug
---

**Version / Umgebung**
- JA-Agent-Version (stdout-Kopf `JA-Prüfung vX.Y.Z` oder `plugin.json`):
- Python-Version und Betriebssystem:
- Installationsweg (Release-`.plugin`, Marketplace, lokaler Klon):

**Beschreibung**
Was ist passiert, was wurde erwartet? Bei Check-Befunden: CHECK-ID (z. B. `US-05`),
Schwere, Befundtext.

**Reproduktion – ausschließlich mit synthetischen Daten**
Niemals echte Mandantendaten anhängen. Idealfall: Reproduktion mit den
Demodaten (`py testdaten/erzeuge_testdaten.py`, Aufruf aus README) oder mit
einem anonymisierten, auf wenige Zeilen gekürzten EXTF-Ausschnitt.

```
Aufruf:
stdout (Kopf + Summenzeile + betroffene Zeile):
```

**Erwartungsbild**
Weicht der Lauf von `testdaten/erwartung.md`/`erwartung.json` ab? Ausgabe von
`py werkzeuge/pruefe_erwartung.py --lauf standard --ausgabe <ordner>`:
