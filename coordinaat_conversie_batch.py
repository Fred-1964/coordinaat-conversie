# =============================================================================
# BATCH COÖRDINAAT CONVERTER
# =============================================================================
# Versie voor het converteren van meerdere bestanden tegelijk.
# Grote bestanden (honderden MB) worden chunksgewijs verwerkt zodat het
# geheugengebruik beperkt blijft. De GUI blijft responsief via threading.
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTS
# Elke library heeft een specifiek doel:
#   tkinter       : standaard Python GUI-toolkit, ingebouwd in Python
#   tkinter.ttk   : verbeterde widgets (Combobox heeft betere opmaak dan tk)
#   pandas        : inlezen en bewerken van tabulaire data (CSV, enz.)
#   filedialog    : dialoogvensters voor bestand- en mapselectie
#   StringVar     : speciale variabele die Tkinter-widgets automatisch updatet
#   os            : hulpmiddelen voor het besturingssysteem (hier: bestanden openen)
#   sys           : toegang tot systeeminfo (hier: PyInstaller detectie)
#   threading     : meerdere taken tegelijk uitvoeren (GUI + conversie)
#   pyproj        : coördinatenconversie via PROJ-bibliotheek
#   pathlib       : objectgeoriënteerde bestandspaden (veiliger dan strings)
#   shapely       : geometrie-bewerkingen (hier: WKT polygon export)
# -----------------------------------------------------------------------------
import tkinter as tk
from tkinter.ttk import Combobox
import pandas as pd
import tkinter.messagebox
from tkinter import filedialog
from tkinter import StringVar
import sys
import threading
import functools
from typing import Literal
from pyproj import Transformer
from pathlib import Path
from shapely.geometry import Polygon


# =============================================================================
# HULPFUNCTIE: ICOONPAD BEPALEN
# =============================================================================
# Wanneer een Python-script gebouwd wordt met PyInstaller tot een .exe,
# worden alle bestanden tijdelijk uitgepakt naar een map in sys._MEIPASS.
# Als het gewoon als .py script draait, bestaat sys._MEIPASS niet.
# getattr(sys, '_MEIPASS', ...) geeft de waarde van _MEIPASS terug als die
# bestaat, anders de opgegeven standaardwaarde (de map van het .py bestand).
# Zo werkt het icoon correct in beide gevallen.
# -----------------------------------------------------------------------------
def resource_path(filename):
    base = getattr(sys, '_MEIPASS', Path(__file__).parent)
    return Path(base) / filename


# =============================================================================
# TKINTER HOOFDVENSTER
# =============================================================================
# root is het hoofdvenster waaraan alle andere widgets worden toegevoegd.
# geometry stelt breedte x hoogte in pixels in.
# resizable(True, True) laat toe het venster te vergroten in beide richtingen.
# grid_columnconfigure(1, weight=1): kolom 1 (de rechterkant met de frames)
#   mag uitrekken als het venster groter wordt. weight=1 betekent dat alle
#   extra ruimte naar die kolom gaat.
# grid_rowconfigure(0, weight=1): rij 0 (het invoerframe met de listbox)
#   mag verticaal uitrekken zodat de bestandenlijst groter wordt.
# -----------------------------------------------------------------------------
root = tk.Tk()
root.geometry('570x780')
root.title("Batch Coördinaat Converter")
root.resizable(True, True)
root.iconbitmap(resource_path("coordinaat_conversie.ico"))
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(0, weight=1)


# =============================================================================
# GLOBALE VARIABELEN
# =============================================================================
# input_files: gewone Python-lijst met de volledige paden van de geselecteerde
#   invoerbestanden. Een gewone lijst (geen StringVar) omdat Tkinter geen
#   ingebouwde variabele heeft voor lijsten.
#
# output_dir: StringVar die het pad van de uitvoermap bijhoudt.
#   StringVar is een speciale Tkinter-variabele: widgets die eraan gekoppeld
#   zijn (via textvariable=...) updaten automatisch als de waarde wijzigt.
# -----------------------------------------------------------------------------
input_files = []

output_dir = StringVar()
output_dir.set("")

# Lijsten voor de dropdown-keuzes in de comboboxen
lst_conversies_input  = ('L72', 'UTM31', 'WGS84', 'L2008')
lst_conversies_output = ('L72', 'UTM31', 'WGS84', 'L2008')
lst_separator_input  = ('komma(decimaal punt)', 'spatie(decimaal punt)', 'tab(decimaal punt)',
                        'punt-komma(decimaal komma)', 'punt-komma(decimaal punt)')
lst_separator_output = ('komma(decimaal punt)', 'spatie(decimaal punt)', 'tab(decimaal punt)',
                        'punt-komma(decimaal komma)', 'punt-komma(decimaal punt)')
# Beschikbare uitvoerextensies: de bestandsnaam blijft gelijk, enkel de
# extensie wordt vervangen door de keuze van de gebruiker.
lst_extensies = ('.asc', '.xyz', '.txt', '.csv', '.pts', '.wkt')

# -----------------------------------------------------------------------------
# CRS-CODES (Coordinate Reference System)
# pyproj gebruikt EPSG-codes om coördinaten te definiëren.
# De dictionary koppelt de naam uit de dropdown aan de juiste EPSG-code.
#   L72    = Belgisch Lambert 1972         (EPSG:31370)
#   UTM31  = Universal Transverse Mercator zone 31N (EPSG:32631)
#   WGS84  = Wereldwijd GPS-stelsel, in graden (EPSG:4326)
#   L2008  = Belgisch Lambert 2008         (EPSG:3812)
# -----------------------------------------------------------------------------
CRS_CODES = {
    "L72":   "EPSG:31370",
    "UTM31": "EPSG:32631",
    "WGS84": "EPSG:4326",
    "L2008": "EPSG:3812",
}

# -----------------------------------------------------------------------------
# KOLOMNAMEN UITVOERBESTAND
# Afhankelijk van het gekozen uitvoerstelsel krijgen de X/Y-kolommen een
# andere naam in het outputbestand.
# -----------------------------------------------------------------------------
HEADERS = {
    "L72":   ("x_L72",   "y_L72"),
    "UTM31": ("x_UTM31", "y_UTM31"),
    "WGS84": ("LAT",     "LON"),
    "L2008": ("x_L2008", "y_L2008"),
}

# -----------------------------------------------------------------------------
# TKINTER SCHAKELAAR-VARIABELEN (BooleanVar / IntVar)
# BooleanVar en IntVar zijn Tkinter-variabelen die gekoppeld worden aan
# checkboxen en radiobuttons. Wanneer de gebruiker een checkbox aanvinkt,
# wijzigt de BooleanVar automatisch. In de code lezen we de waarde op met .get()
#
#   diepte_switch            : Z-waarden omdraaien van teken (diepte <-> hoogte)
#   header_input_switch      : eerste rij van het invoerbestand overslaan
#   header_output_switch     : kolomnamen schrijven in het uitvoerbestand
#   eerste_kolom_naam_switch : eerste kolom bevat een punt-ID (geen coördinaat)
#   reductievlak_conversie_keuze : 0=geen, 1=LAT→TAW, 2=TAW→LAT
#   reductievlak_waarde      : welke correctiewaarde gebruiken (per haven/zone)
#   status_var               : tekst die in het statuslabel getoond wordt
# -----------------------------------------------------------------------------
diepte_switch                = tk.BooleanVar(value=False)
header_input_switch          = tk.BooleanVar(value=False)
header_output_switch         = tk.BooleanVar(value=True)
eerste_kolom_naam_switch     = tk.BooleanVar(value=False)
reductievlak_conversie_keuze = tk.IntVar(value=0)
reductievlak_waarde          = tk.IntVar(value=0)
status_var                   = tk.StringVar(value="")


# =============================================================================
# HULPFUNCTIES: SCHEIDINGSTEKENS OPHALEN
# =============================================================================
# De gebruiker kiest in de dropdown een leesbare omschrijving zoals
# "komma(decimaal punt)". De functies vertalen die keuze naar de eigenlijke
# tekens die pandas nodig heeft: een scheidingsteken en een decimaalteken.
# Beide functies geven een tuple terug: (scheidingsteken, decimaalteken).
# Voorbeeld: "punt-komma(decimaal komma)" → (";", ",")
# -----------------------------------------------------------------------------
def scheidingsteken_ophalen():
    # scheidingsteken en decimaalteken voor het INVOERBESTAND
    input_separators = {
        'komma(decimaal punt)':     (",",  "."),
        'spatie(decimaal punt)':    (" ",  "."),
        'tab(decimaal punt)':       ("\t", "."),
        'punt-komma(decimaal komma)': (";", ","),
        'punt-komma(decimaal punt)':  (";", "."),
    }
    return input_separators[combo_separator_in.get()]


def scheidingsteken_geven():
    # scheidingsteken en decimaalteken voor het UITVOERBESTAND
    output_separators = {
        'komma(decimaal punt)':     (",",  "."),
        'spatie(decimaal punt)':    (" ",  "."),
        'tab(decimaal punt)':       ("\t", "."),
        'punt-komma(decimaal komma)': (";", ","),
        'punt-komma(decimaal punt)':  (";", "."),
    }
    return output_separators[combo_separator_out.get()]


# =============================================================================
# CGP-BESTAND INLEZEN
# =============================================================================
# Een *.cgp bestand heeft een eigen formaat met "=" als scheidingsteken en
# een kopregel die overgeslagen moet worden. Deze functie zet het om naar
# een standaard pandas DataFrame zodat de rest van de code het gewoon kan
# verwerken. CGP-bestanden zijn doorgaans klein, dus chunking is hier niet nodig.
# -----------------------------------------------------------------------------
def cgp_to_dataframe(filename: str) -> pd.DataFrame:
    with open(filename, "r", encoding="utf-8") as f:
        # strip() verwijdert witruimte aan begin en einde van elke regel
        # replace("=", ",") maakt van "naam=x=y" een komma-gescheiden rij
        # de conditie "if line.strip()" slaat lege regels over
        lines = [line.strip().replace("=", ",") for line in f if line.strip()]

    lines = lines[1:]  # eerste regel is de kopregel, die slaan we over

    # Elke tekstlijn splitsen op komma en van de resulterende lijsten een
    # DataFrame maken. Elke deellijst wordt één rij in de tabel.
    # dtype=object voorkomt dat pandas 2.x kolommen als StringDtype opslaat,
    # zodat de float-conversie hieronder correct werkt.
    df = pd.DataFrame([line.split(",") for line in lines], dtype=object)

    # Spaties verwijderen uit de eerste kolom (bevat de puntnamen)
    df.iloc[:, 0] = df.iloc[:, 0].str.replace(" ", "", regex=False)

    # Kolommen 1 t/m einde zijn coördinaten: converteren naar float.
    # Bij pd.read_csv gebeurt dit automatisch via de decimal-parameter,
    # maar hier lezen we handmatig in als strings, dus we doen het expliciet.
    df.iloc[:, 1:] = df.iloc[:, 1:].apply(pd.to_numeric)
    return df


# =============================================================================
# DIEPTE OMDRAAIEN
# =============================================================================
# Vermenigvuldigt de Z-kolom met -1. Zo worden negatieve dieptewaarden
# positief (of omgekeerd). Wordt enkel opgeroepen als de checkbox aanstaat.
# -----------------------------------------------------------------------------
def depth_toggle(df):
    df['Z'] *= -1
    return df


# =============================================================================
# REDUCTIEVLAK CORRECTIE (LAT ↔ TAW)
# =============================================================================
# Voegt een correctiewaarde toe aan of trekt ze af van de Z-kolom.
# Elke haven of zone heeft een eigen offset tussen LAT (getijreferentievlak)
# en TAW (Tweede Algemene Waterpassing, het Belgische hoogtestelsel).
# De key in de dictionary stemt overeen met de waarde van de radiobutton.
# reductievlak_conversie_keuze bepaalt de richting (1=LAT→TAW, 2=TAW→LAT).
# reductievlak_waarde bepaalt welke correctiewaarde gebruikt wordt.
# -----------------------------------------------------------------------------
def lat_to_taw(df):
    conversie_waardes = {
        0: 0.69,  # EUT/NZT
        1: 0.72,  # DUD
        2: 0.73,  # VCS/BOS
        3: 0.74,  # ROS
        4: 0.75,  # SKO
        5: 0.70,  # AVG Antwerpen
        6: 0.25,  # ZB
    }
    conversie_waarde = conversie_waardes[reductievlak_waarde.get()]

    if reductievlak_conversie_keuze.get() == 1:
        df['Z'] -= conversie_waarde   # LAT naar TAW: aftrekken
    elif reductievlak_conversie_keuze.get() == 2:
        df['Z'] += conversie_waarde   # TAW naar LAT: optellen
    return df


# =============================================================================
# VERWERK ÉÉN DATAFRAME-CHUNK
# =============================================================================
# Dit is de kern van de conversie. De functie krijgt één stuk data binnen
# (een volledige DataFrame voor kleine bestanden, of een "chunk" van 100.000
# rijen voor grote bestanden) en geeft een getransformeerd DataFrame terug.
#
# Parameters:
#   chunk       : het stukje data om te verwerken
#   transformer : het pyproj Transformer-object dat de wiskundige conversie doet
#   x_header    : naam van de X-kolom in het uitvoerbestand
#   y_header    : naam van de Y-kolom in het uitvoerbestand
#
# De functie houdt rekening met het aantal kolommen:
#   2 kolommen : alleen X en Y
#   3 kolommen : X, Y en Z  (of punt-ID, X, Y als eerste kolom punt is)
#   4 kolommen : X, Y, Z en een extra variabele  (of punt-ID, X, Y, Z)
# -----------------------------------------------------------------------------
def _verwerk_chunk(chunk, transformer, x_header, y_header):
    aantal_kolommen = len(chunk.columns)

    # chunk.iloc[:, 0] betekent: alle rijen (:), kolom 0
    # .values geeft een numpy-array terug, wat sneller werkt met pyproj
    # transform() geeft twee arrays terug: de getransformeerde X en Y waarden
    if not eerste_kolom_naam_switch.get():
        # standaard: kolom 0 = X, kolom 1 = Y
        x_output, y_output = transformer.transform(
            chunk.iloc[:, 0].values,
            chunk.iloc[:, 1].values
        )
    else:
        # als eerste kolom een punt-ID is: kolom 1 = X, kolom 2 = Y
        x_output, y_output = transformer.transform(
            chunk.iloc[:, 1].values,
            chunk.iloc[:, 2].values
        )

    # Nieuw DataFrame bouwen met de geconverteerde waarden.
    # We gebruiken een dictionary: sleutel = kolomnaam, waarde = data.
    if aantal_kolommen == 2:
        df_output = pd.DataFrame({x_header: x_output, y_header: y_output})

    elif aantal_kolommen == 3:
        if not eerste_kolom_naam_switch.get():
            # kolom 2 is de Z-waarde (hoogte/diepte)
            df_output = pd.DataFrame({
                x_header: x_output,
                y_header: y_output,
                'Z': chunk.iloc[:, 2].values
            })
        else:
            # kolom 0 is de punt-ID, geen Z aanwezig
            df_output = pd.DataFrame({
                'point': chunk.iloc[:, 0].values,
                x_header: x_output,
                y_header: y_output
            })

    elif aantal_kolommen == 4:
        if not eerste_kolom_naam_switch.get():
            # kolom 2 = Z, kolom 3 = extra variabele
            df_output = pd.DataFrame({
                x_header: x_output,
                y_header: y_output,
                'Z':   chunk.iloc[:, 2].values,
                'VAR': chunk.iloc[:, 3].values
            })
        else:
            # kolom 0 = punt-ID, kolom 3 = Z
            df_output = pd.DataFrame({
                'point': chunk.iloc[:, 0].values,
                x_header: x_output,
                y_header: y_output,
                'Z': chunk.iloc[:, 3].values
            })

    else:
        raise ValueError(f"Onverwacht aantal kolommen: {aantal_kolommen}. Maximum is 4.")

    # Afronden: WGS84 werkt in graden (kleine getallen), dus 6 decimalen.
    # Andere stelsels werken in meters, 2 decimalen volstaat (cm-nauwkeurigheid).
    if combo_conv_out.get() == "WGS84":
        df_output[x_header] = df_output[x_header].round(6)
        df_output[y_header] = df_output[y_header].round(6)
    else:
        df_output[x_header] = df_output[x_header].round(2)
        df_output[y_header] = df_output[y_header].round(2)

    # Z-kolom nabewerken als die aanwezig is
    if 'Z' in df_output.columns:
        df_output['Z'] = df_output['Z'].round(2)

        # Diepte omdraaien indien de checkbox aanstaat
        if diepte_switch.get():
            df_output = depth_toggle(df_output)

        # Reductievlak correctie indien een richting is gekozen (≠ 0)
        if reductievlak_conversie_keuze.get() != 0:
            df_output = lat_to_taw(df_output)
            df_output['Z'] = df_output['Z'].round(2)  # opnieuw afronden na correctie

    return df_output


# =============================================================================
# CONVERSIE VAN ÉÉN BESTAND
# =============================================================================
# Verwerkt één invoerbestand volledig en schrijft het resultaat weg.
# Voor grote bestanden wordt pandas' chunksize-functie gebruikt:
# in plaats van het hele bestand in één keer in te laden, leest pandas
# telkens 100.000 rijen. Elke batch wordt direct weggeschreven, waarna
# het geheugen vrijgegeven wordt. Zo blijft het RAM-gebruik laag.
#
# Het uitvoerbestand wordt als volgt opgebouwd:
#   - eerste chunk : mode='w' (nieuw bestand aanmaken), header optioneel
#   - volgende chunks: mode='a' (toevoegen aan bestaand bestand), geen header
# -----------------------------------------------------------------------------
def conversie_een_bestand(input_pad, output_pad: str):
    separator_in,  decimal_in  = scheidingsteken_ophalen()
    separator_out, decimal_out = scheidingsteken_geven()

    # De geselecteerde stelselnamen ophalen en omzetten naar EPSG-codes
    coord_in  = CRS_CODES[combo_conv_in.get()]
    coord_out = CRS_CODES[combo_conv_out.get()]

    # De kolomnamen voor het uitvoerbestand ophalen
    x_header, y_header = HEADERS[combo_conv_out.get()]

    # Transformer aanmaken: berekent de wiskundige projectie tussen de twee stelsels.
    # always_xy=True wordt hier NIET gebruikt: pyproj volgt dan de officiële volgorde
    # van het CRS (bijv. lat/lon voor WGS84). In België/Europa is de notatie
    # 51.xxxx, 4.xxxx (breedtegraad eerst) gangbaarder, wat overeenkomt met die volgorde.
    transformer = Transformer.from_crs(coord_in, coord_out)

    # CGP-bestanden hebben een apart inleesformaat en zijn doorgaans klein:
    # die lezen we in één keer in zonder chunking.
    if Path(input_pad).suffix.lower() == ".cgp":
        df = cgp_to_dataframe(input_pad)
        df_output = _verwerk_chunk(df, transformer, x_header, y_header)

        # WKT-EXPORT (Well-Known Text) — optie voor PDS2000-gebruikers
        # ---------------------------------------------------------------
        # WKT is een standaard tekstformaat om geometrieën te beschrijven,
        # bijv. POLYGON ((4.123 51.456, 4.124 51.457, ...))
        # Dit is een niche-optie die enkel gebruikt wordt in het hydrografisch
        # programma PDS2000 (Teledyne RESON). Daarin definieert een CGP-bestand
        # een werkgebied (polygon) en kan dat als WKT worden geïmporteerd.
        # De WKT wordt opgebouwd uit de geconverteerde X- en Y-kolommen.
        if Path(output_pad).suffix.lower() == ".wkt":
            coords = list(df_output.iloc[:, :2].itertuples(index=False, name=None))
            poly = Polygon(coords)
            with open(output_pad, 'w') as f:
                f.write(poly.wkt)
            return  # klaar, geen CSV-schrijven meer nodig

        df_output.to_csv(output_pad, index=False, sep=separator_out,
                         decimal=decimal_out, header=header_output_switch.get())
        return  # klaar, geen verdere verwerking nodig

    # Voor alle andere bestandstypes: sla de titelrij over als de checkbox aanstaat.
    # skiprows=1 slaat de eerste rij over vóór het inlezen begint.
    skiprows = 1 if header_input_switch.get() else 0

    # pd.read_csv met chunksize geeft geen DataFrame terug, maar een iterator.
    # Telkens we "for chunk in chunk_iter" doen, leest pandas de volgende
    # 100.000 rijen in. Dit is het sleutelconcept voor geheugenefficiëntie.
    chunk_iter = pd.read_csv(
        input_pad,
        delimiter=separator_in,
        decimal=decimal_in,
        header=None,       # geen kolomnamen in het bestand zelf inlezen
        skiprows=skiprows,
        chunksize=100_000  # maximaal 100.000 rijen tegelijk in het geheugen
    )

    eerste_chunk = True
    for chunk in chunk_iter:
        # Verwerk dit stuk data
        df_output = _verwerk_chunk(chunk, transformer, x_header, y_header)

        # Schrijfmodus bepalen:
        #   eerste chunk → 'w': nieuw bestand aanmaken (overschrijft bestaand)
        #   volgende chunks → 'a': achteraan toevoegen aan het bestand
        # De header (kolomnamen) schrijven we enkel bij de eerste chunk.
        schrijf_header = header_output_switch.get() and eerste_chunk
        mode: Literal["w", "a"] = 'w' if eerste_chunk else 'a'

        df_output.to_csv(output_pad, index=False, sep=separator_out,
                         decimal=decimal_out, header=schrijf_header, mode=mode)

        # Expliciete del: geef het geheugen onmiddellijk vrij na het schrijven.
        # Python's garbage collector doet dit normaal automatisch, maar bij
        # grote DataFrames is het veiliger om het zelf te doen.
        del df_output
        eerste_chunk = False


# =============================================================================
# UITVOERBESTANDSNAAM GENEREREN
# =============================================================================
# In de batch-versie is er geen dialoog om per bestand een naam te kiezen.
# De naam wordt automatisch samengesteld uit:
#   - de originele bestandsnaam zonder extensie (.stem)
#   - de extensie die de gebruiker koos in de combobox
#   - in de uitvoermap die de gebruiker selecteerde
#
# Voorbeeld: invoer = C:\data\meting_01.txt, map = C:\output, extensie = .asc
#            uitvoer = C:\output\meting_01.asc
# -----------------------------------------------------------------------------
def output_bestandsnaam(input_pad):
    naam     = Path(input_pad).stem       # bestandsnaam zonder extensie
    extensie = combo_extensie_out.get()   # gekozen extensie uit de combobox
    return str(Path(output_dir.get()) / (naam + extensie))


# =============================================================================
# BATCH STARTEN (vanuit de GUI-knop)
# =============================================================================
# Controleert of de vereiste invoer aanwezig is en start dan de batch
# in een aparte thread. De knop wordt geblokkeerd om dubbele klikken te
# vermijden. Na afloop (of bij fout) wordt de knop terug ingeschakeld.
# -----------------------------------------------------------------------------
def run_batch():
    if not input_files:
        tkinter.messagebox.showwarning("Geen bestanden", "Selecteer eerst invoerbestanden.")
        return
    if not output_dir.get():
        tkinter.messagebox.showwarning("Geen uitvoermap", "Selecteer eerst een uitvoermap.")
        return

    btn_run.config(state="disabled")  # knop blokkeren tijdens verwerking

    # De eigenlijke verwerking starten in een aparte achtergrond-thread.
    # daemon=True betekent: als het hoofdprogramma sluit, stopt ook deze thread.
    threading.Thread(target=_batch_thread, daemon=True).start()


# =============================================================================
# BATCH THREAD (de eigenlijke verwerking, draait op de achtergrond)
# =============================================================================
# Deze functie draait in een aparte thread zodat de GUI niet bevriest.
#
# BELANGRIJK: Tkinter is niet "thread-safe". Widgets mag je NIET rechtstreeks
# aanpassen vanuit een achtergrond-thread. De veilige manier is root.after(0, func):
# dit plant de functie in op de hoofdthread (de GUI-thread), die hem zo snel
# mogelijk uitvoert. Zo blijft alles gesynchroniseerd.
#
# In de for-lus wordt elk bestand volledig verwerkt (alle chunks weggeschreven)
# vóór het volgende begint. Zo staat er nooit een half bestand op schijf.
# -----------------------------------------------------------------------------
def _batch_thread():
    totaal = len(input_files)

    # Uitvoermap aanmaken als die nog niet bestaat.
    # parents=True : ook tussenliggende mappen aanmaken indien nodig
    # exist_ok=True : geen fout als de map al bestaat
    Path(output_dir.get()).mkdir(parents=True, exist_ok=True)

    for i, bestand in enumerate(input_files, start=1):
        try:
            # Status updaten via root.after: veilige manier om GUI aan te passen
            # vanuit een thread. De string wordt meteen berekend en via partial
            # doorgegeven als nul-argumenten callable (thread-safe, type-correct).
            root.after(0, functools.partial(status_var.set, f"Bezig... {i}/{totaal}"))  # type: ignore[arg-type]

            output_pad = output_bestandsnaam(bestand)
            conversie_een_bestand(bestand, output_pad)

        except Exception as e:
            # Bij een fout: foutmelding tonen en de batch stopzetten.
            # We geven de bestandsnaam en foutmelding mee in de lambda.
            naam = Path(bestand).name
            root.after(0, functools.partial(tkinter.messagebox.showerror, 'Foutje', f'Fout bij bestand:\n{naam}\n\n{e}'))  # type: ignore[arg-type]
            root.after(0, functools.partial(status_var.set, f"Fout bij bestand {i}/{totaal}"))  # type: ignore[arg-type]
            root.after(0, functools.partial(btn_run.config, state="normal"))  # type: ignore[arg-type]
            return  # stop de lus, ga niet verder met de rest

    # Alle bestanden succesvol verwerkt
    root.after(0, functools.partial(status_var.set, f"Klaar! {totaal}/{totaal} bestanden geconverteerd."))  # type: ignore[arg-type]
    root.after(0, functools.partial(btn_run.config, state="normal"))  # type: ignore[arg-type]


# =============================================================================
# BESTANDSSELECTIE FUNCTIES
# =============================================================================

def open_files():
    # askopenfilenames (meervoud!) opent een dialoog waarbij de gebruiker
    # meerdere bestanden tegelijk kan selecteren (Ctrl+klik of Shift+klik).
    # Het resultaat is een tuple van volledige bestandspaden.
    # global input_files: we schrijven naar de globale variabele, niet naar
    # een lokale kopie. Zonder "global" zou Python een nieuwe lokale variabele
    # aanmaken en de globale lijst niet updaten.
    global input_files
    status_var.set("")

    bestanden = filedialog.askopenfilenames(
        filetypes=[('txt Bestanden', '.txt'), ('xyz Bestanden', '.xyz'),
                   ('pts Bestanden', '.pts'), ('csv Bestanden', '.csv'),
                   ('asc Bestanden', '.asc'), ('cgp Bestanden', '.cgp'),
                   ('All Files', '.*')]
    )

    if bestanden:
        input_files = list(bestanden)

        # Listbox leegmaken en opnieuw vullen met de geselecteerde bestandsnamen.
        # We tonen enkel de naam (Path.name), niet het volledige pad.
        lb_bestanden.delete(0, tk.END)
        for f in input_files:
            lb_bestanden.insert(tk.END, Path(f).name)


def open_output_dir():
    # askdirectory opent een dialoog voor het selecteren van een map (geen bestand).
    status_var.set("")
    pad = filedialog.askdirectory()
    if pad:
        output_dir.set(pad)  # StringVar updaten → het tekstveld in de GUI updatet automatisch


# =============================================================================
# RECHTERMUISKLIK-MENU (knippen/kopiëren/plakken)
# =============================================================================
# Tkinter voegt standaard geen rechtermuisknop-menu toe aan invoervelden.
# Deze functie maakt een tijdelijk menu aan op de positie van de muisklik.
# event.x_root / event.y_root zijn de absolute schermcoördinaten van de klik.
# tearoff=0: het menu kan niet losgemaakt worden als apart venster.
# event_generate stuurt een virtueel event naar het widget, alsof de gebruiker
# de sneltoets gebruikt.
# -----------------------------------------------------------------------------
def show_context_menu(event, entry_widget):
    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="Knippen",
                             command=lambda: entry_widget.event_generate("<<Cut>>"))
    context_menu.add_command(label="Kopiëren",
                             command=lambda: entry_widget.event_generate("<<Copy>>"))
    context_menu.add_command(label="Plakken",
                             command=lambda: entry_widget.event_generate("<<Paste>>"))
    context_menu.tk_popup(event.x_root, event.y_root)


# =============================================================================
# OPBOUW VAN HET FORMULIER
# =============================================================================
# Het venster is opgedeeld in een raster van rijen en kolommen.
# Kolom 0: smalle kolom voor de knoppen (links)
# Kolom 1: brede kolom voor de frames met opties (rechts, rekt uit)
#
# De frames worden per paar aangemaakt:
#   f1/f2  : knoppen/opties voor de invoerbestanden
#   f3/f4  : knoppen/opties voor de uitvoermap
#   f5/f6  : reductievlak-instellingen
#   f7/f8  : de converteerknop
#   f9/f10 : het statuslabel
#
# LabelFrame: een Frame met een zichtbare rand en een titel.
# Frame: een onzichtbaar kadertype, enkel voor groepering en positionering.
#
# sticky bepaalt hoe een widget zijn beschikbare cel opvult:
#   N/S/E/W = boven/onder/rechts/links
#   "nsew"  = alle vier richtingen (helemaal uitrekken)
#   tk.NE   = rechts-boven uitlijnen
# padx/pady = ruimte rondom het widget (in pixels)
# =============================================================================

# --- Rij 0: Invoer bestanden ---
f1 = tk.Frame(root)
f1.grid(row=0, column=0, sticky=tk.NE, padx=2, pady=3)

f2 = tk.LabelFrame(root, relief="groove", text="Invoer Bestanden", font="bold")
f2.grid(row=0, column=1, sticky="nsew", padx=2, pady=3)
f2.grid_columnconfigure(0, weight=1)  # inhoud van f2 mag horizontaal uitrekken
f2.grid_rowconfigure(0, weight=1)     # rij 0 van f2 (de listbox) mag verticaal uitrekken

# --- Rij 1: Uitvoer map ---
f3 = tk.Frame(root)
f3.grid(row=1, column=0, sticky=tk.NE, padx=2, pady=3)

f4 = tk.LabelFrame(root, relief="groove", text="Uitvoer Map", font="bold")
f4.grid(row=1, column=1, sticky="new", padx=2, pady=5)
f4.grid_columnconfigure(0, weight=1)

# --- Rij 2: Reductievlak ---
f5 = tk.Frame(root)
f5.grid(row=2, column=0, sticky=tk.NW, padx=2, pady=3)

f6 = tk.LabelFrame(root, relief="groove", text="Reductievlak (LAT Negatief!!)")
f6.grid(row=2, column=1, sticky=tk.NW, padx=2, pady=3)

# --- Rij 3: Converteerknop ---
f7 = tk.Frame(root)
f7.grid(row=3, column=0, sticky=tk.NW, padx=2, pady=5)

f8 = tk.Frame(root)
f8.grid(row=3, column=1, sticky=tk.NW, padx=2, pady=3)

# --- Rij 4: Statuslabel ---
f9 = tk.Frame(root)
f9.grid(row=4, column=0, sticky=tk.NW, padx=2, pady=3)

f10 = tk.Frame(root)
f10.grid(row=4, column=1, sticky=tk.NW, padx=2, pady=3)


# =============================================================================
# WIDGETS: INVOER BESTANDEN (f1 / f2)
# =============================================================================

# Knop om de bestandsselectie te openen
btn_input = tk.Button(f1, text="Invoer", command=open_files, font="bold", width=10, height=2)
btn_input.grid(row=0, column=0, sticky=tk.NE, pady=2, padx=2)

# Subframe voor de listbox + scrollbar samen.
# De listbox en scrollbar worden naast elkaar geplaatst via een eigen grid.
# frame_lb fungeert als een container zodat de scrollbar netjes naast de
# listbox zit en mee uitzet wanneer het venster vergroot wordt.
frame_lb = tk.Frame(f2)
frame_lb.grid(row=0, column=0, sticky="nsew", pady=2, padx=2)
frame_lb.grid_columnconfigure(0, weight=1)  # listbox kolom mag uitrekken
frame_lb.grid_rowconfigure(0, weight=1)     # listbox rij mag uitrekken

# Listbox: toont de namen van de geselecteerde bestanden.
# selectmode=EXTENDED: gebruiker kan meerdere items selecteren met Ctrl/Shift
# (nuttig voor toekomstige uitbreidingen, bv. geselecteerde items verwijderen)
lb_bestanden = tk.Listbox(frame_lb, height=6, bg="lightyellow", selectmode=tk.EXTENDED)
lb_bestanden.grid(row=0, column=0, sticky="nsew")

# Scrollbar koppelen aan de listbox:
#   command=lb_bestanden.yview : scrollbar stuurt de listbox aan
#   yscrollcommand=scrollbar.set : listbox stuurt de scrollbar positie bij
scrollbar_lb = tk.Scrollbar(frame_lb, orient="vertical", command=lb_bestanden.yview)
scrollbar_lb.grid(row=0, column=1, sticky="ns")
lb_bestanden.config(yscrollcommand=scrollbar_lb.set)

# Combobox: dropdown voor het invoercoördinatenstelsel
combo_conv_in = Combobox(f2, values=lst_conversies_input, height=10, width=30)
combo_conv_in.grid(row=1, column=0, sticky=tk.W, pady=2, padx=2)
combo_conv_in.set('UTM31')  # standaardwaarde

# Combobox: dropdown voor het scheidingsteken van het invoerbestand
combo_separator_in = Combobox(f2, values=lst_separator_input, height=10, width=30)
combo_separator_in.grid(row=2, column=0, sticky=tk.W, pady=2, padx=2)
combo_separator_in.set('spatie(decimaal punt)')

# Checkbox: eerste kolom bevat een punt-ID in plaats van een coördinaat
checkbox_eerste_kolom = tk.Checkbutton(f2, text="Eerste kolom bevat point-id",
                                        variable=eerste_kolom_naam_switch)
checkbox_eerste_kolom.grid(row=3, column=0, sticky=tk.W, pady=2, padx=2)

# Checkbox: eerste rij van het invoerbestand is een titelrij en moet overgeslagen worden
checkbox_header_input = tk.Checkbutton(f2, text="Negeer titelrij",
                                        variable=header_input_switch)
checkbox_header_input.grid(row=4, column=0, sticky=tk.W, pady=2, padx=2)


# =============================================================================
# WIDGETS: UITVOER MAP (f3 / f4)
# =============================================================================

# Knop om de map te selecteren
btn_output = tk.Button(f3, text="Uitvoer", font="bold", command=open_output_dir, width=10, height=2)
btn_output.grid(row=0, column=0, sticky=tk.E, pady=2, padx=2)

# Tekstveld dat het pad van de uitvoermap toont.
# state="readonly": gebruiker kan niet typen, enkel lezen.
# readonlybackground: achtergrondkleur in readonly-modus.
# textvariable=output_dir: het veld updatet automatisch wanneer output_dir wijzigt.
txt_output = tk.Entry(f4, textvariable=output_dir, relief="sunken", width=70,
                      state="readonly", readonlybackground="lightyellow")
txt_output.grid(row=0, column=0, sticky="new", pady=2, padx=2)
# Rechtermuisklik-menu aan het tekstveld koppelen
txt_output.bind("<Button-3>", lambda event: show_context_menu(event, txt_output))

# Combobox: dropdown voor het uitvoercoördinatenstelsel
combo_conv_out = Combobox(f4, values=lst_conversies_output, height=10, width=30)
combo_conv_out.grid(row=1, column=0, sticky=tk.W, pady=2, padx=2)
combo_conv_out.set('L72')

# Combobox: dropdown voor het scheidingsteken van het uitvoerbestand
combo_separator_out = Combobox(f4, values=lst_separator_output, height=10, width=30)
combo_separator_out.grid(row=2, column=0, sticky=tk.W, pady=2, padx=2)
combo_separator_out.set('komma(decimaal punt)')

# Label + combobox voor de uitvoerextensie.
# In de batch-versie kiezen we de extensie eenmalig voor alle bestanden.
# De bestandsnaam blijft gelijk aan de invoernaam, enkel de extensie wijzigt.
tk.Label(f4, text="Uitvoer extensie:").grid(row=3, column=0, sticky=tk.W, pady=(4, 0), padx=2)
combo_extensie_out = Combobox(f4, values=lst_extensies, height=10, width=15)
combo_extensie_out.grid(row=4, column=0, sticky=tk.W, pady=2, padx=2)
combo_extensie_out.set('.asc')

# Checkbox: Z-waarden omdraaien van teken (positief ↔ negatief)
checkbox_diepte_hoogte = tk.Checkbutton(f4, text="Wissel hoogte/diepte",
                                         variable=diepte_switch)
checkbox_diepte_hoogte.grid(row=5, column=0, sticky=tk.W, pady=2, padx=2)

# Checkbox: kolomnamen als eerste rij toevoegen aan het uitvoerbestand
checkbox_header_output = tk.Checkbutton(f4, text="Titelrij toevoegen",
                                         variable=header_output_switch)
checkbox_header_output.grid(row=6, column=0, sticky=tk.W, pady=2, padx=2)


# =============================================================================
# WIDGETS: REDUCTIEVLAK (f5 / f6)
# =============================================================================
# Radiobuttons: slechts één keuze tegelijk mogelijk.
# variable=reductievlak_conversie_keuze : alle knoppen in deze groep delen
#   dezelfde IntVar. Klikken op een knop zet die IntVar op de bijhorende value.
# Linker kolom (column=0): richting van de correctie
# Rechter kolom (column=1): grootte van de correctiewaarde per zone

radio_button_reductievlak = tk.Radiobutton(f6, text="NONE",
                                            value=0, variable=reductievlak_conversie_keuze)
radio_button_reductievlak.grid(row=0, column=0, sticky=tk.W, pady=2, padx=2)
radio_button_reductievlak = tk.Radiobutton(f6, text="LAT naar TAW",
                                            value=1, variable=reductievlak_conversie_keuze)
radio_button_reductievlak.grid(row=1, column=0, sticky=tk.W, pady=2, padx=2)
radio_button_reductievlak = tk.Radiobutton(f6, text="TAW naar LAT",
                                            value=2, variable=reductievlak_conversie_keuze)
radio_button_reductievlak.grid(row=2, column=0, sticky=tk.W, pady=2, padx=2)

radio_button_reductievlak_waarde = tk.Radiobutton(f6, text="EUT/NZT(0.69m)",
                                                    value=0, variable=reductievlak_waarde)
radio_button_reductievlak_waarde.grid(row=0, column=1, sticky=tk.W, pady=2, padx=2)
radio_button_reductievlak_waarde = tk.Radiobutton(f6, text="DUD(0.72m)",
                                                    value=1, variable=reductievlak_waarde)
radio_button_reductievlak_waarde.grid(row=1, column=1, sticky=tk.W, pady=2, padx=2)
radio_button_reductievlak_waarde = tk.Radiobutton(f6, text="VCS/BOS(0.73m)",
                                                    value=2, variable=reductievlak_waarde)
radio_button_reductievlak_waarde.grid(row=2, column=1, sticky=tk.W, pady=2, padx=2)
radio_button_reductievlak_waarde = tk.Radiobutton(f6, text="ROS(0.74m)",
                                                    value=3, variable=reductievlak_waarde)
radio_button_reductievlak_waarde.grid(row=3, column=1, sticky=tk.W, pady=2, padx=2)
radio_button_reductievlak_waarde = tk.Radiobutton(f6, text="SKO(0.75m)",
                                                    value=4, variable=reductievlak_waarde)
radio_button_reductievlak_waarde.grid(row=4, column=1, sticky=tk.W, pady=2, padx=2)
radio_button_reductievlak_waarde = tk.Radiobutton(f6, text="AVG Antw(0.70m)",
                                                    value=5, variable=reductievlak_waarde)
radio_button_reductievlak_waarde.grid(row=5, column=1, sticky=tk.W, pady=2, padx=2)
radio_button_reductievlak_waarde = tk.Radiobutton(f6, text="ZB(0.25m)",
                                                    value=6, variable=reductievlak_waarde)
radio_button_reductievlak_waarde.grid(row=6, column=1, sticky=tk.W, pady=2, padx=2)


# =============================================================================
# WIDGETS: CONVERTEERKNOP (f7 / f8)
# =============================================================================
# De knop roept run_batch() op. Na klikken wordt hij uitgeschakeld (disabled)
# tot de verwerking klaar is, zodat de gebruiker niet per ongeluk twee keer klikt.
# -----------------------------------------------------------------------------
btn_run = tk.Button(f8, text="Converteer batch", font="bold", command=run_batch, width=15, height=2)
btn_run.grid(row=0, column=0, sticky=tk.E, pady=2, padx=2)


# =============================================================================
# WIDGETS: STATUSLABEL (f9 / f10)
# =============================================================================
# Het label toont de voortgang tijdens de batch (bijv. "Bezig... 3/10")
# en het eindresultaat ("Klaar! 10/10 bestanden geconverteerd.").
# textvariable=status_var: het label updatet automatisch wanneer status_var
# gewijzigd wordt, ook vanuit de achtergrond-thread (via root.after).
# -----------------------------------------------------------------------------
lbl_status = tk.Label(
    f10,
    textvariable=status_var,
    font=("TkDefaultFont", 15, "bold"),
    fg="#b30000",   # donkerrood
    bg="#f2f2f2",   # lichtgrijs
)
lbl_status.grid(row=0, column=0, sticky=tk.NW, pady=2, padx=2)


# =============================================================================
# HOOFDLUS
# =============================================================================
# root.mainloop() start de Tkinter event loop: het programma wacht op
# gebruikersacties (klikken, typen, ...) en verwerkt ze één voor één.
# Deze regel blokkeert tot het venster gesloten wordt.
# =============================================================================
root.mainloop()
