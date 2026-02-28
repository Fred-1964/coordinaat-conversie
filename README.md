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