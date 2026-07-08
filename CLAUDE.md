# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Taal en werkwijze

- Communiceer met de gebruiker in het **Nederlands**.
- Leg elke codewijziging uit: wat er verandert en waarom (de gebruiker wil ervan leren). Eerst uitleggen, dan pas aanpassen.
- De scripts hebben bewust **uitgebreide Nederlandstalige commentaarblokken** met educatieve uitleg. Houd die stijl aan bij wijzigingen: nieuw gedrag ook in het commentaar documenteren.

## Commando's

Alles draait via de virtualenv in `.venv` (Python 3.13):

```powershell
# Script rechtstreeks draaien (GUI-app)
.venv\Scripts\python.exe pdf_naar_base64.py

# Exe bouwen (verschijnt in dist\)
.venv\Scripts\pyinstaller.exe pdf_naar_base64.spec --noconfirm
```

Er zijn geen tests en geen linter. Na een codewijziging hoort de bijbehorende exe opnieuw gebouwd te worden; zowel het script als `dist\*.exe` worden gecommit (de exes zitten in git).

## Structuur

Drie **zelfstandige Tkinter GUI-tools**, elk één script + één PyInstaller-spec + één exe in `dist\`. Er zijn geen gedeelde modules: patronen zoals `resource_path()`, het rechtermuisklik-menu en de achtergrond-thread zijn bewust gekopieerd tussen de scripts, zodat elk script op zichzelf staat.

| Script | Doel |
|---|---|
| `coordinaat_conversie_v3.py` | Coördinaatconversie van één bestand (L72, UTM31, WGS84, L2008), met reductievlakcorrectie (LAT/TAW). Gebruikt pyproj, pandas, shapely. |
| `coordinaat_conversie_batch.py` | Zelfde conversies, meerdere bestanden tegelijk. |
| `pdf_naar_base64.py` | PDF's naar base64-chunks in een CSV voor Power BI. Alleen standaardbibliotheek. |

Gedeelde patronen in alle drie:

- **`resource_path()`**: pad naar het icoon (`coordinaat_conversie.ico`) dat werkt als .py én als exe (via `sys._MEIPASS`). Het icoon moet daarom in de spec onder `datas` staan.
- **Verwerking in een achtergrond-thread**: Tkinter is niet thread-safe; GUI-updates vanuit de thread lopen altijd via `root.after(0, functools.partial(...))`.

## Domeinkennis

- **Coördinaatvolgorde**: `always_xy=True` wordt bewust NIET gebruikt in `Transformer.from_crs()`. pyproj volgt dan de officiële CRS-asvolgorde (breedtegraad eerst voor WGS84), wat de gangbare notatie in België is.
- **CGP-formaat (PDS2000)**: kopregel `[POINTS]`, daarna regels `Point(1) = 149146.5,215289.7` (naam=x,y). Coördinaten zijn altijd Lambert 72 (EPSG:31370). De naamkolom (kolom 0) is er altijd, ongeacht de "eerste kolom is punt-id"-checkbox.
- **Power BI CSV** (`pdf_naar_base64.py`): formaat `ID;B01;...;B50`, chunks van 32.759 tekens (Power BI-limiet is 32.766 per tekstveld), max ~1,2 MB per PDF. Het CSV-bestand wordt **aangevuld (append)**, niet overschreven; de kopregel wordt alleen geschreven als het bestand nieuw of leeg is.
