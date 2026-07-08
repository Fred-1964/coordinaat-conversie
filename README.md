# Coördinaat Converter

Een eenvoudige Windows-applicatie om coördinaten te converteren tussen de meest gebruikte Belgische en internationale coördinatenstelsels:

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

---

## Downloaden

Ga naar de [Releases](../../releases) pagina en download de gewenste `.exe`.

Geen installatie nodig — gewoon dubbelklikken en starten.

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