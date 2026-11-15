# Coördinaat Converter

Een eenvoudige applicatie (Windows en Mac) om coördinaten te converteren tussen de meest gebruikte Belgische en internationale coördinatenstelsels:

- **L72** – Belgisch Lambert 72
- **UTM31** – Universal Transverse Mercator zone 31
- **WGS84** – GPS-coördinaten (breedtegraad/lengtegraad)
- **L2008** – Belgisch Lambert 2008

---

## Versies

| Versie | Beschrijving |
|---|---|
| **Single** (`coordinaat_conversie_v3.exe`) | Converteert één bestand per keer. Ondersteunt ook reductievlakcorrectie (LAT/TAW). |
| **Batch** (`coordinaat_conversie_batch.exe`) | Converteert meerdere bestanden tegelijk in één keer. |
| **Single voor Mac** (`Coordinaat Conversie v3.app`) | Zelfde als Single, voor Macs met Apple Silicon (M1 t/m M4). |
| **Batch voor Mac** (`Coordinaat Conversie Batch.app`) | Zelfde als Batch, voor Macs met Apple Silicon (M1 t/m M4). |

---

## Downloaden

Ga naar de [Releases](../../releases) pagina en download de gewenste `.exe`.

Geen installatie nodig — gewoon dubbelklikken en starten.

### Mac-versies (Apple Silicon: M1, M2, M3, M4)

De Mac-apps worden automatisch gebouwd en getest door GitHub. Python hoeft niet op de Mac te staan.

1. Ga naar de release [Mac-apps (laatste build)](../../releases/tag/mac-laatste).
2. Download onder **Assets** het gewenste bestand:
   - `Coordinaat-Conversie-v3-Mac.zip` — één bestand per keer
   - `Coordinaat-Conversie-Batch-Mac.zip` — meerdere bestanden tegelijk
3. Pak het uit (dubbelklikken) en sleep de app naar de map **Apps**.

Deze release wordt bij elke wijziging aan de Mac-versies automatisch vervangen door de nieuwste build.

**Eerste keer openen** (voor elke app één keer). De app is niet door Apple gekeurd (dat vereist een betaald ontwikkelaarsaccount), dus macOS houdt hem de eerste keer tegen:

1. Dubbelklik op de app en klik in de melding op **Gereed**.
2. Open **Systeeminstellingen > Privacy en beveiliging**, scrol naar beneden en klik bij de melding over de app op **Open toch**.
3. Bevestig met je wachtwoord of Touch ID. Daarna start de app voortaan gewoon.

Lukt dat niet, dan kan het ook via de Terminal:

```bash
xattr -dr com.apple.quarantine "/Applications/Coordinaat Conversie v3.app"
```

```bash
xattr -dr com.apple.quarantine "/Applications/Coordinaat Conversie Batch.app"
```

De apps werken niet op oudere Macs met een Intel-processor.

---

## Gebruik

### Invoerbestand
- Ondersteunde formaten: `.txt`, `.asc`, `.xyz`, `.pts`, `.csv`, `.cgp`
- Het bestand moet kolommen bevatten met X- en Y-coördinaten (en optioneel Z)

### Opties
- **Scheidingsteken**: komma, spatie, tab of punt-komma
- **Titelrij**: vink aan als je bestand een kolomnamenrij heeft
- **Eerste kolom is punt-id**: vink aan als de eerste kolom een naam/nummer bevat
- **Wissel hoogte/diepte**: keert het teken van de Z-waarde om

### Uitvoerbestand
- Kies zelf naam en locatie
- Ondersteunde formaten: `.asc`, `.xyz`, `.wkt`

---

## Extra tool: PDF naar Base64 Converter (Power BI)

`pdf_naar_base64.exe` zet één of meerdere PDF-bestanden om naar base64-tekst
in een CSV-bestand dat rechtstreeks in Power BI ingelezen kan worden.

### Werking
- Elke PDF wordt één rij in de CSV: `ID;B01;B02;...;B50`
- De **ID** is de bestandsnaam (inclusief `.pdf`)
- De base64-tekst wordt opgeknipt in stukken van 32.759 tekens verdeeld
  over de kolommen B01 t/m B50, omdat Power BI maximaal 32.766 tekens
  per tekstveld toelaat. In Power BI worden de kolommen weer samengevoegd.
- Maximale bestandsgrootte: ~1,2 MB per PDF (50 kolommen × 32.759 tekens)

### Toevoegen in plaats van overschrijven
Bestaat het gekozen CSV-bestand al, dan worden nieuwe rijen **onderaan
toegevoegd** (append) — het bestand wordt niet overschreven. De kopregel
wordt alleen geschreven als het bestand nieuw of leeg is.

Let op: dezelfde PDF twee keer converteren geeft twee rijen met dezelfde ID.