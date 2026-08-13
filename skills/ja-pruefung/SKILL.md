---
name: ja-pruefung
description: Jahresabschluss-Plausibilitätsprüfung auf DATEV-Buchungsstapeln mit deterministischer Prüf-Pipeline (Python, 73 Checks in vier Prüfebenen) und KI-Beurteilungsschicht; erzeugt einen strukturierten Excel-Prüfbericht. Verwenden bei "Jahresabschluss prüfen", "JA-Prüfung", "Buchungsstapel prüfen", "DATEV-Export prüfen", "Buchhaltung plausibilisieren", "Kasse negativ", "Prüfbericht erstellen", "Bilanz- und GuV-Konten durchgehen".
---

# Jahresabschluss-Prüfung (DATEV-Buchungsstapel)

Arbeitsteilung strikt einhalten: **Alle eindeutigen Regeln laufen
deterministisch im Python-Code** (vollständiger Katalog:
`references/pruefkatalog.md`). **Die KI beurteilt ausschließlich die von der
Pipeline exportierten Kandidaten** – Muster und Kontext, die sich nicht in
Regeln fassen lassen (sachfremde Buchungen, Privatveranlassung,
Aktivierungsfragen). Niemals selbst Salden nachrechnen, Buchungen zählen oder
Befunde behaupten, die die Pipeline nicht gemeldet hat.

## Eingaben

1. **Buchungsstapel im DATEV-Format** (EXTF/DTVF-CSV, Formatkategorie 21) –
   Pflicht. Export in DATEV Rechnungswesen: Bestände → Exportieren →
   Buchungsstapel (DATEV-Format); alle Monate des Wirtschaftsjahres inkl.
   EB-Buchungen exportieren.
2. Optional **SuSa** als CSV (Spalten `Konto;Saldo`, Soll positiv) –
   aktiviert Bestandsabgleich (SB-05) und USt-/VSt-Verprobung (US-06/07).
3. Optional **Vorjahres-SuSa** (`--susa-vorjahr`, gleiches Format) –
   aktiviert EB-Abgleich gegen die Schlussbilanz des Vorjahres (VJ-01)
   und den GuV-Vorjahresvergleich (VJ-02).
4. Optional **OPOS-Liste** als CSV (`Konto;…;Belegdatum;Fälligkeit;Betrag`) –
   aktiviert Altposten-Prüfung (OP-03), Nebenbuch-Abgleich (OP-05/06)
   und die Alterungsanalyse.
5. Optional **Kontenplan/Kontenbeschriftungen** (EXTF Kat. 20) – liegt
   die Datei im selben Ordner wie die Stapel, wird sie automatisch
   erkannt (mandantenindividueller Kontenplan: Nummer + Bezeichnung).
6. Optional **Folgejahres-Stapel** (`--stapel-folgejahr`, gleicher
   Export für den Beginn des Folgejahres, ein Januar-Stapel genügt) –
   aktiviert die aufwandsseitige Cut-off-Nachlaufprüfung CO-02
   (Fenster 14 Tage nach WJ-Ende; Vollständigkeit der
   Verbindlichkeiten). Getrennt vom Prüfjahres-Ordner übergeben, nie
   in den `--stapel`-Ordner legen. Ohne Lieferung begründeter Skip,
   kein Mangel.

Fehlt der Stapel: Pfade erfragen bzw. die Exportanleitung geben. Ohne
Stapeldaten keine Prüfung und keine behaupteten Ergebnisse.
Formatreferenzen mit Quellen-Links (DATEV-Dokumente, Kategorie-Codes):
`references/pruefkatalog.md`, Abschnitt „Formatreferenzen".

## Ablauf

0. Sofern der Nutzer kein Berichtsformat vorgegeben hat, per Frage
   klären: Excel-Prüfbericht (Standard: Cockpit, Bilanz/GuV
   formelverknüpft, Befundblätter, Buchungsjournal mit
   Quelle-Hyperlinks) und/oder Power-BI-Projekt (`--pbi`: PBIP mit
   verknüpftem Modell befunde ↔ salden ↔ buchungen/opos/ki_kandidaten
   und sieben Berichtsseiten, öffnet in Power BI Desktop; dort lädt
   erst „Aktualisieren" die Daten – bis dahin zeigen die Visuals
   „(Leer)"). Excel, JSON und CSVs (befunde, salden, buchungen, opos,
   ki_kandidaten) entstehen bei jedem Lauf – die Antwort steuert das
   `--pbi`-Flag und was gesendet wird.
1. Pipeline ausführen (ein Aufruf; Ordner oder Einzeldateien übergeben):

   ```
   py "${CLAUDE_PLUGIN_ROOT}/werkzeuge/ja_pruefung.py" --stapel <ordner-oder-dateien> [--stapel-folgejahr <ordner-oder-dateien>] [--susa <csv>] [--susa-vorjahr <csv>] [--opos <csv>] [--rechtsform <form>] [--mandant "<Name>"] [--pbi] [--ausgabe <ordner>]
   ```

   Rechtsform beim Nutzer erfragen bzw. aus dem Kontext übernehmen
   (`einzelunternehmen|personengesellschaft|kapitalgesellschaft`) – sie
   steuert PP-01/02/04 und SB-10; DQ-02 verprobt die Angabe gegen
   Mandantenname und Kontenbild und meldet Widersprüche als
   Hoch-Befund (dann NICHT weiterinterpretieren, sondern Rechtsform
   klären und Lauf wiederholen). Bei Personengesellschaften im Resümee
   auf die Mitunternehmer-Zusatzprüfungen hinweisen (Kapitalkonten,
   Sonder-/Ergänzungsbilanzen, § 15a EStG – Katalog Kap. 8/14).

   `--skr 03|04` nur setzen, wenn die automatische Erkennung laut stdout
   falsch liegt. Kontenbereiche/Parameter: `werkzeuge/konten_config.json`.
2. stdout-Zusammenfassung auswerten. Die Excel-Datei nicht parsen;
   `befunde.json` nur punktuell lesen, wenn Details nötig sind.
3. KI-Schicht: `llm_kandidaten.json` aus dem Ausgabeordner lesen und **jeden**
   Kandidaten beurteilen. `llm_beurteilung.json` in den Ausgabeordner
   schreiben:

   ```json
   {"zusammenfassung": "4-6 Sätze Management Summary",
    "beurteilungen": [{"id": "K001", "urteil": "...", "begruendung": "1 Satz",
                       "schwere": "hoch|mittel|hinweis|keine",
                       "konfidenz": "hoch|mittel|niedrig"}]}
   ```

   `urteil` ∈ `sachfremd-verdacht | privat-verdacht | aktivierung-pruefen |
   doppelerfassung-verdacht | unauffaellig | unklar`. Begründung fachlich in
   einem Satz; Norm nennen, wo tragfähig (z. B. § 4 Abs. 5 EStG, § 15 UStG,
   § 6 Abs. 1 Nr. 1a EStG). Deterministische Befunde nicht überschreiben oder
   relativieren – die KI-Schicht ergänzt, sie ersetzt nicht.
4. Einarbeiten:

   ```
   py "${CLAUDE_PLUGIN_ROOT}/werkzeuge/llm_einarbeiten.py" --bericht <Pruefbericht.xlsx> --beurteilungen <llm_beurteilung.json>
   ```

5. Excel-Bericht an den Nutzer senden. Kurzresümee im Chat: Befunde nach
   Schwere, die Hoch-Befunde einzeln, Kernaussagen der KI-Durchsicht sowie
   die zusätzlichen Prüfungen mit der jeweils benötigten Datenquelle
   (als Erweiterungsangebot, nicht als Mangel). Keine Tabellen-Dumps.

## Kosten- und Datendisziplin

- Die Kandidatenmenge ist kriterienbasiert und skaliert mit den
  Auffälligkeiten, nicht mit der Buchungszahl. Beurteilung kompakt, ein
  Satz je Kandidat. Bei mehr als ~100 Kandidaten in Batches von 50–100
  arbeiten (IDs fortlaufend, eine Gesamt-Zusammenfassung am Ende); bei
  mehr als ~1.000 den Nutzer auf den Aufwand hinweisen und Priorisierung
  anbieten (`llm_kandidat_min_eur` erhöhen oder `llm_kandidaten_max`
  setzen – Abschneidung wird im Bericht ausgewiesen). Keine Subagenten
  erforderlich.
- Ausgabeordner: vom Nutzer genannter Ort, sonst `JA-Pruefung/` neben den
  Eingabedaten.
- Kandidaten enthalten echte Buchungstexte (Mandantendaten): nur beurteilen,
  nicht in den Chat kopieren, nicht extern verwenden.

## Grenzen (im Resümee transparent machen)

- Der Stapel führt Bruttoumsätze mit BU-Schlüsseln; Netto- und Steuerwerte
  sind rechnerisch abgeleitet. EB-Werte nur enthalten, wenn mitexportiert.
- Kontenbereiche sind SKR03/SKR04-Standardannahmen
  (`konten_config.json`) – bei individuellen Kontenplänen anpassen.
- Bestandsabgleich und Verprobungen erfordern die SuSa, OPOS-Checks die
  OPOS-Liste, Benford ≥ 300 GuV-Buchungen. Solche Checks weist der Bericht
  als „zusätzliche Prüfung" mit der benötigten Quelle aus – dem Nutzer
  anbieten, die Quelle nachzuliefern (Abdeckung steigt dann automatisch).
