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

### Mac-versie (toegevoegd november 2026)

De Mac-app wordt **niet lokaal op Windows gebouwd**: PyInstaller kan niet kruislings bouwen. Dat doet GitHub Actions op een Apple Silicon-runner (`macos-15`, arm64):

- Workflow: `.github/workflows/build-mac.yml`. Start automatisch bij een push die `coordinaat_conversie_v3_mac.py`, de Mac-spec, het `.icns`-icoon of de workflow zelf wijzigt; handmatig via Actions > "Bouw Mac-app" > "Run workflow".
- Resultaat: artifact `Coordinaat-Conversie-v3-Mac` (zip met `Coordinaat Conversie v3.app`). De Mac-app zit dus **niet** in `dist\` in git.
- De workflow controleert zelf: arm64, geldige ondertekening, `--zelftest` (script én ingepakte app) en of het venster open blijft.

Op een Mac zelf bouwen kan ook:

```bash
pip install pandas pyproj shapely pyinstaller
python coordinaat_conversie_v3_mac.py --zelftest
pyinstaller coordinaat_conversie_v3_mac.spec --noconfirm
```

## Structuur

Drie **zelfstandige Tkinter GUI-tools**, elk één script + één PyInstaller-spec + één exe in `dist\`, plus één **Mac-variant** van de v3-tool. Er zijn geen gedeelde modules: patronen zoals `resource_path()`, het rechtermuisklik-menu en de achtergrond-thread zijn bewust gekopieerd tussen de scripts, zodat elk script op zichzelf staat.

| Script | Doel |
|---|---|
| `coordinaat_conversie_v3.py` | Coördinaatconversie van één bestand (L72, UTM31, WGS84, L2008), met reductievlakcorrectie (LAT/TAW). Gebruikt pyproj, pandas, shapely. |
| `coordinaat_conversie_batch.py` | Zelfde conversies, meerdere bestanden tegelijk. |
| `coordinaat_conversie_v3_mac.py` | Mac-versie (Apple Silicon) van `coordinaat_conversie_v3.py`. Zelfde rekenlogica, alleen de OS-afhankelijke delen verschillen. |
| `pdf_naar_base64.py` | PDF's naar base64-chunks in een CSV voor Power BI. Alleen standaardbibliotheek. |

Gedeelde patronen in alle drie:

- **`resource_path()`**: pad naar het icoon (`coordinaat_conversie.ico`) dat werkt als .py én als exe (via `sys._MEIPASS`). Het icoon moet daarom in de spec onder `datas` staan.
- **Verwerking in een achtergrond-thread**: Tkinter is niet thread-safe; GUI-updates vanuit de thread lopen altijd via `root.after(0, functools.partial(...))`.

## Mac-versie: verschillen met de Windows-versie

`coordinaat_conversie_v3_mac.py` is een **kopie** van `coordinaat_conversie_v3.py` (bewust geen gedeelde module, zie hierboven). Een wijziging in de rekenlogica moet dus in **beide** scripts gebeuren. Bovenaan het Mac-script staat het volledige overzicht; kort:

- **Geen `resource_path()` / `root.iconbitmap()`**: een `.ico` geeft op macOS een fout. Het icoon is `coordinaat_conversie.icns` en wordt door `BUNDLE` in de spec in de app gezet.
- **`open_bestand()`** (commando `open`) in plaats van `os.startfile()`.
- **`bind_contextmenu()`**: rechtsklik is `<Button-2>`, `<Button-3>` én `<Control-Button-1>`.
- **Donkere modus**: lichtgele velden hebben uitdrukkelijk `fg="black"`; het statuslabel heeft geen vaste achtergrondkleur.
- **Bestandsvensters**: `'*'` in plaats van `'.*'` voor alle bestanden, een gecombineerd filter vooraan, en "Annuleren" wordt afgevangen.
- **`--zelftest`**: zet één bekend L72-punt om naar WGS84 en stopt met exitcode 0 of 1. Wijzigt de standaardconversie of de uitvoeropmaak, dan moet `zelftest()` mee aangepast worden.
- **Spec**: onedir (`EXE` > `COLLECT` > `BUNDLE`), `target_arch='arm64'`, `upx=False`. De app is alleen ad-hoc ondertekend (geen Apple Developer-account), dus Gatekeeper blokkeert de eerste start; de README legt uit hoe je dat oplost.

## Domeinkennis

- **Coördinaatvolgorde**: `always_xy=True` wordt bewust NIET gebruikt in `Transformer.from_crs()`. pyproj volgt dan de officiële CRS-asvolgorde (breedtegraad eerst voor WGS84), wat de gangbare notatie in België is.
- **CGP-formaat (PDS2000)**: kopregel `[POINTS]`, daarna regels `Point(1) = 149146.5,215289.7` (naam=x,y). Coördinaten zijn altijd Lambert 72 (EPSG:31370). De naamkolom (kolom 0) is er altijd, ongeacht de "eerste kolom is punt-id"-checkbox.
- **Power BI CSV** (`pdf_naar_base64.py`): formaat `ID;B01;...;B50`, chunks van 32.759 tekens (Power BI-limiet is 32.766 per tekstveld), max ~1,2 MB per PDF. Het CSV-bestand wordt **aangevuld (append)**, niet overschreven; de kopregel wordt alleen geschreven als het bestand nieuw of leeg is.
