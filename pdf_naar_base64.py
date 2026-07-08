# =============================================================================
# PDF NAAR BASE64 CONVERTER (voor Power BI)
# =============================================================================
# Zet één of meerdere PDF-bestanden om naar base64-tekst en schrijft die weg
# in een CSV-bestand dat rechtstreeks in Power BI ingelezen kan worden.
#
# Waarom opsplitsen in stukken (chunks)?
#   Power BI heeft een limiet van 32.766 tekens per tekstveld. Een PDF van
#   bijvoorbeeld 130 kB wordt als base64 zo'n 175.000 tekens lang — veel te
#   groot voor één cel. Daarom knippen we de base64-tekst in stukken van
#   32.759 tekens en verdelen die over de kolommen B01 t/m B50.
#   In Power BI worden die kolommen daarna weer aan elkaar geplakt.
#
# Het uitvoerformaat is identiek aan dat van de online tool (base64.guru)
# die eerder handmatig gebruikt werd:
#   ID;B01;B02;...;B50
#   bestandsnaam.pdf;<chunk1>;<chunk2>;...;;
#
# Bestaat het gekozen CSV-bestand al, dan worden de nieuwe rijen ONDERAAN
# toegevoegd (append); het bestand wordt dus niet overschreven.
# =============================================================================

# -----------------------------------------------------------------------------
# IMPORTS
# Alles komt uit de standaardbibliotheek van Python, er hoeft dus niets
# geïnstalleerd te worden met pip:
#   tkinter       : standaard Python GUI-toolkit, ingebouwd in Python
#   filedialog    : dialoogvensters voor bestand- en mapselectie
#   StringVar     : speciale variabele die Tkinter-widgets automatisch updatet
#   base64        : omzetten van binaire data (bytes) naar base64-tekst
#   csv           : correct wegschrijven van CSV-bestanden (regelt zelf de
#                   scheidingstekens en regeleindes)
#   sys           : toegang tot systeeminfo (hier: PyInstaller detectie)
#   threading     : conversie op de achtergrond zodat de GUI niet bevriest
#   functools     : partial() om functies met argumenten door te geven aan
#                   root.after() (thread-veilige GUI-updates)
#   pathlib       : objectgeoriënteerde bestandspaden (veiliger dan strings)
# -----------------------------------------------------------------------------
import tkinter as tk
import tkinter.messagebox
from tkinter import filedialog
from tkinter import StringVar
import base64
import csv
import sys
import threading
import functools
from pathlib import Path


# =============================================================================
# INSTELLINGEN VAN HET UITVOERFORMAAT
# =============================================================================
# CHUNK_GROOTTE: aantal tekens base64 per kolom. Power BI laat maximaal
#   32.766 tekens per tekstveld toe; 32.759 zit daar veilig onder en is
#   dezelfde waarde die de online tool gebruikte.
#
# AANTAL_KOLOMMEN: het aantal B-kolommen in de CSV (B01 t/m B50).
#   50 kolommen x 32.759 tekens = maximaal 1.637.950 tekens base64,
#   wat overeenkomt met een PDF van ongeveer 1,2 MB. Grotere PDF's passen
#   niet en geven een duidelijke foutmelding.
#
# CSV_SEPARATOR: puntkomma, zoals in het bestaande Power BI-dashboard.
# -----------------------------------------------------------------------------
CHUNK_GROOTTE   = 32_759
AANTAL_KOLOMMEN = 50
CSV_SEPARATOR   = ";"


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
# grid_columnconfigure(1, weight=1): kolom 1 (de rechterkant met de frames)
#   mag uitrekken als het venster groter wordt.
# grid_rowconfigure(0, weight=1): rij 0 (het invoerframe met de listbox)
#   mag verticaal uitrekken zodat de bestandenlijst groter wordt.
# -----------------------------------------------------------------------------
root = tk.Tk()
root.geometry('570x520')
root.title("PDF naar Base64 Converter (Power BI)")
root.resizable(True, True)
root.iconbitmap(resource_path("coordinaat_conversie.ico"))
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(0, weight=1)


# =============================================================================
# GLOBALE VARIABELEN
# =============================================================================
# input_files: gewone Python-lijst met de volledige paden van de geselecteerde
#   PDF-bestanden. Een gewone lijst (geen StringVar) omdat Tkinter geen
#   ingebouwde variabele heeft voor lijsten.
#
# output_file: StringVar die het pad van het uitvoer-CSV-bestand bijhoudt.
#   StringVar is een speciale Tkinter-variabele: widgets die eraan gekoppeld
#   zijn (via textvariable=...) updaten automatisch als de waarde wijzigt.
#
# status_var: tekst die in het statuslabel getoond wordt.
# -----------------------------------------------------------------------------
input_files = []

output_file = StringVar()
output_file.set("")

status_var = tk.StringVar(value="")


# =============================================================================
# KERN VAN HET PROGRAMMA: PDF OMZETTEN NAAR BASE64-CHUNKS
# =============================================================================
# Deze functie doet het eigenlijke werk voor één PDF:
#   1. Het bestand binair inlezen ("rb" = read binary, want een PDF is
#      geen tekst maar ruwe bytes).
#   2. De bytes omzetten naar base64. base64.b64encode() geeft bytes terug,
#      met .decode("ascii") maken we er een gewone tekst-string van
#      (base64 bestaat per definitie enkel uit ASCII-tekens: A-Z a-z 0-9 + / =).
#   3. De lange string opknippen in stukken van CHUNK_GROOTTE tekens.
#      De slice b64_tekst[i:i + CHUNK_GROOTTE] pakt telkens het volgende stuk;
#      range(start, stop, stap) levert de beginposities: 0, 32759, 65518, ...
#   4. Controleren of het aantal stukken in de beschikbare kolommen past.
#   5. De lijst aanvullen met lege strings tot exact AANTAL_KOLOMMEN,
#      zodat elke rij in de CSV evenveel velden heeft als de kopregel.
#
# De functie geeft de volledige CSV-rij terug: [bestandsnaam, chunk1, ..., ""].
# -----------------------------------------------------------------------------
def pdf_naar_csv_rij(pdf_pad):
    # Stap 1: PDF binair inlezen
    pdf_bytes = Path(pdf_pad).read_bytes()

    # Stap 2: bytes -> base64-tekst
    b64_tekst = base64.b64encode(pdf_bytes).decode("ascii")

    # Stap 3: opknippen in stukken van CHUNK_GROOTTE tekens
    chunks = [b64_tekst[i:i + CHUNK_GROOTTE]
              for i in range(0, len(b64_tekst), CHUNK_GROOTTE)]

    # Stap 4: past het in de beschikbare kolommen?
    if len(chunks) > AANTAL_KOLOMMEN:
        max_mb = (AANTAL_KOLOMMEN * CHUNK_GROOTTE * 3 / 4) / 1_000_000
        raise ValueError(
            f"PDF is te groot: {len(chunks)} chunks nodig, "
            f"maximum is {AANTAL_KOLOMMEN} (PDF max. ~{max_mb:.1f} MB)."
        )

    # Stap 5: aanvullen met lege velden tot AANTAL_KOLOMMEN
    chunks += [""] * (AANTAL_KOLOMMEN - len(chunks))

    # De ID-kolom is de bestandsnaam inclusief extensie (Path.name),
    # net zoals in het bestaande Power BI-dashboard.
    return [Path(pdf_pad).name] + chunks


# =============================================================================
# CONVERSIE STARTEN (vanuit de GUI-knop)
# =============================================================================
# Controleert of de vereiste invoer aanwezig is en start dan de conversie
# in een aparte thread. De knop wordt geblokkeerd om dubbele klikken te
# vermijden. Na afloop (of bij fout) wordt de knop terug ingeschakeld.
# -----------------------------------------------------------------------------
def run_conversie():
    if not input_files:
        tkinter.messagebox.showwarning("Geen bestanden", "Selecteer eerst PDF-bestanden.")
        return
    if not output_file.get():
        tkinter.messagebox.showwarning("Geen uitvoerbestand", "Selecteer eerst een uitvoer CSV-bestand.")
        return

    btn_run.config(state="disabled")  # knop blokkeren tijdens verwerking

    # De eigenlijke verwerking starten in een aparte achtergrond-thread.
    # daemon=True betekent: als het hoofdprogramma sluit, stopt ook deze thread.
    threading.Thread(target=_conversie_thread, daemon=True).start()


# =============================================================================
# CONVERSIE THREAD (de eigenlijke verwerking, draait op de achtergrond)
# =============================================================================
# Deze functie draait in een aparte thread zodat de GUI niet bevriest.
#
# BELANGRIJK: Tkinter is niet "thread-safe". Widgets mag je NIET rechtstreeks
# aanpassen vanuit een achtergrond-thread. De veilige manier is root.after(0, func):
# dit plant de functie in op de hoofdthread (de GUI-thread), die hem zo snel
# mogelijk uitvoert. Zo blijft alles gesynchroniseerd.
#
# Werkwijze:
#   - Eerst worden ALLE rijen berekend en verzameld in een lijst.
#   - Pas daarna wordt het CSV-bestand geschreven.
#   Zo blijft een bestaand CSV-bestand intact als één van de PDF's een
#   fout geeft (bijv. te groot): er wordt dan niets weggeschreven.
#
# Het bestand wordt geopend in append-modus ("a"): nieuwe rijen komen
# onderaan het bestaande bestand te staan. Bestaat het bestand nog niet
# (of is het leeg), dan wordt eerst de kopregel geschreven; anders staat
# die er al en slaan we hem over (een dubbele kopregel zou in Power BI
# als datarij ingelezen worden).
#
# Het csv-module detail "newline=''" bij open(): het csv-module regelt zelf
# de regeleindes (\r\n volgens de CSV-standaard). Zonder newline='' zou
# Windows er dubbele lege regels van maken.
# -----------------------------------------------------------------------------
def _conversie_thread():
    totaal = len(input_files)
    rijen = []

    for i, bestand in enumerate(input_files, start=1):
        try:
            # Status updaten via root.after: veilige manier om GUI aan te passen
            # vanuit een thread. functools.partial maakt van "status_var.set met
            # deze tekst" één aanroepbaar geheel dat de GUI-thread later uitvoert.
            root.after(0, functools.partial(status_var.set, f"Bezig... {i}/{totaal}"))

            rijen.append(pdf_naar_csv_rij(bestand))

        except Exception as e:
            # Bij een fout: foutmelding tonen en de verwerking stopzetten.
            naam = Path(bestand).name
            root.after(0, functools.partial(tkinter.messagebox.showerror, 'Foutje',
                                            f'Fout bij bestand:\n{naam}\n\n{e}'))
            root.after(0, functools.partial(status_var.set, f"Fout bij bestand {i}/{totaal}"))
            root.after(0, functools.partial(btn_run.config, state="normal"))
            return  # stop de lus, ga niet verder met de rest

    try:
        # Alle PDF's zijn succesvol omgezet: nu pas het CSV-bestand schrijven.
        # De kopregel: ID;B01;B02;...;B50
        # f"B{n:02d}" formatteert het nummer met voorloopnul: 1 -> "B01"
        kopregel = ["ID"] + [f"B{n:02d}" for n in range(1, AANTAL_KOLOMMEN + 1)]

        # Kopregel is alleen nodig als het bestand nog niet bestaat of leeg is
        # (st_size is de bestandsgrootte in bytes).
        uitvoer_pad = Path(output_file.get())
        kopregel_nodig = not uitvoer_pad.exists() or uitvoer_pad.stat().st_size == 0

        with open(uitvoer_pad, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=CSV_SEPARATOR)
            if kopregel_nodig:
                writer.writerow(kopregel)
            writer.writerows(rijen)

    except Exception as e:
        # Bijvoorbeeld: het CSV-bestand staat nog open in Excel (vergrendeld)
        root.after(0, functools.partial(tkinter.messagebox.showerror, 'Foutje',
                                        f'Fout bij het schrijven van het CSV-bestand:\n\n{e}'))
        root.after(0, functools.partial(status_var.set, "Fout bij schrijven CSV"))
        root.after(0, functools.partial(btn_run.config, state="normal"))
        return

    # Alles gelukt
    root.after(0, functools.partial(status_var.set, f"Klaar! {totaal}/{totaal} PDF's toegevoegd aan CSV."))
    root.after(0, functools.partial(btn_run.config, state="normal"))


# =============================================================================
# BESTANDSSELECTIE FUNCTIES
# =============================================================================

def open_files():
    # askopenfilenames (meervoud!) opent een dialoog waarbij de gebruiker
    # meerdere bestanden tegelijk kan selecteren (Ctrl+klik of Shift+klik).
    # Het resultaat is een tuple van volledige bestandspaden.
    # global input_files: we schrijven naar de globale variabele, niet naar
    # een lokale kopie.
    global input_files
    status_var.set("")

    bestanden = filedialog.askopenfilenames(
        filetypes=[('PDF Bestanden', '.pdf'), ('All Files', '.*')]
    )

    if bestanden:
        input_files = list(bestanden)

        # Listbox leegmaken en opnieuw vullen met de geselecteerde bestandsnamen.
        # We tonen enkel de naam (Path.name), niet het volledige pad.
        lb_bestanden.delete(0, tk.END)
        for f in input_files:
            lb_bestanden.insert(tk.END, Path(f).name)


def open_output_file():
    # asksaveasfilename opent een "Opslaan als"-dialoog. De gebruiker kiest
    # map én bestandsnaam in één keer. defaultextension voegt automatisch
    # .csv toe als de gebruiker geen extensie typt. initialfile is de
    # voorgestelde naam (zelfde als het bestaande Power BI-bestand).
    # confirmoverwrite=False: geen "Vervangen?"-waarschuwing bij een bestaand
    # bestand, want er wordt niet overschreven maar toegevoegd (append).
    status_var.set("")
    pad = filedialog.asksaveasfilename(
        defaultextension=".csv",
        initialfile="BaggerviewBase64data.csv",
        confirmoverwrite=False,
        filetypes=[('csv Bestanden', '.csv'), ('All Files', '.*')]
    )
    if pad:
        output_file.set(pad)  # StringVar updaten -> het tekstveld updatet automatisch


# =============================================================================
# RECHTERMUISKLIK-MENU (knippen/kopiëren/plakken)
# =============================================================================
# Tkinter voegt standaard geen rechtermuisknop-menu toe aan invoervelden.
# Deze functie maakt een tijdelijk menu aan op de positie van de muisklik.
# event.x_root / event.y_root zijn de absolute schermcoördinaten van de klik.
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
#   f1/f2 : knop/lijst voor de invoer-PDF's
#   f3/f4 : knop/tekstveld voor het uitvoer-CSV-bestand
#   f5/f6 : de converteerknop
#   f7/f8 : het statuslabel
#
# LabelFrame: een Frame met een zichtbare rand en een titel.
# sticky bepaalt hoe een widget zijn cel opvult ("nsew" = alle richtingen).
# =============================================================================

# --- Rij 0: Invoer PDF's ---
f1 = tk.Frame(root)
f1.grid(row=0, column=0, sticky=tk.NE, padx=2, pady=3)

f2 = tk.LabelFrame(root, relief="groove", text="Invoer PDF Bestanden", font="bold")
f2.grid(row=0, column=1, sticky="nsew", padx=2, pady=3)
f2.grid_columnconfigure(0, weight=1)  # inhoud van f2 mag horizontaal uitrekken
f2.grid_rowconfigure(0, weight=1)     # rij 0 van f2 (de listbox) mag verticaal uitrekken

# --- Rij 1: Uitvoer CSV ---
f3 = tk.Frame(root)
f3.grid(row=1, column=0, sticky=tk.NE, padx=2, pady=3)

f4 = tk.LabelFrame(root, relief="groove", text="Uitvoer CSV Bestand (rijen worden toegevoegd)", font="bold")
f4.grid(row=1, column=1, sticky="new", padx=2, pady=5)
f4.grid_columnconfigure(0, weight=1)

# --- Rij 2: Converteerknop ---
f5 = tk.Frame(root)
f5.grid(row=2, column=0, sticky=tk.NW, padx=2, pady=5)

f6 = tk.Frame(root)
f6.grid(row=2, column=1, sticky=tk.NW, padx=2, pady=3)

# --- Rij 3: Statuslabel ---
f7 = tk.Frame(root)
f7.grid(row=3, column=0, sticky=tk.NW, padx=2, pady=3)

f8 = tk.Frame(root)
f8.grid(row=3, column=1, sticky=tk.NW, padx=2, pady=3)


# =============================================================================
# WIDGETS: INVOER PDF'S (f1 / f2)
# =============================================================================

# Knop om de bestandsselectie te openen
btn_input = tk.Button(f1, text="Invoer", command=open_files, font="bold", width=10, height=2)
btn_input.grid(row=0, column=0, sticky=tk.NE, pady=2, padx=2)

# Subframe voor de listbox + scrollbar samen, zodat de scrollbar netjes
# naast de listbox zit en mee uitzet wanneer het venster vergroot wordt.
frame_lb = tk.Frame(f2)
frame_lb.grid(row=0, column=0, sticky="nsew", pady=2, padx=2)
frame_lb.grid_columnconfigure(0, weight=1)  # listbox kolom mag uitrekken
frame_lb.grid_rowconfigure(0, weight=1)     # listbox rij mag uitrekken

# Listbox: toont de namen van de geselecteerde PDF's.
# selectmode=EXTENDED: gebruiker kan meerdere items selecteren met Ctrl/Shift
lb_bestanden = tk.Listbox(frame_lb, height=8, bg="lightyellow", selectmode=tk.EXTENDED)
lb_bestanden.grid(row=0, column=0, sticky="nsew")

# Scrollbar koppelen aan de listbox:
#   command=lb_bestanden.yview : scrollbar stuurt de listbox aan
#   yscrollcommand=scrollbar.set : listbox stuurt de scrollbar positie bij
scrollbar_lb = tk.Scrollbar(frame_lb, orient="vertical", command=lb_bestanden.yview)
scrollbar_lb.grid(row=0, column=1, sticky="ns")
lb_bestanden.config(yscrollcommand=scrollbar_lb.set)

# Informatielabel: herinnert de gebruiker aan de maximale bestandsgrootte
max_mb = (AANTAL_KOLOMMEN * CHUNK_GROOTTE * 3 / 4) / 1_000_000
lbl_info = tk.Label(f2, text=f"Max. ~{max_mb:.1f} MB per PDF "
                             f"({AANTAL_KOLOMMEN} kolommen x {CHUNK_GROOTTE} tekens)")
lbl_info.grid(row=1, column=0, sticky=tk.W, pady=2, padx=2)


# =============================================================================
# WIDGETS: UITVOER CSV (f3 / f4)
# =============================================================================

# Knop om het uitvoerbestand te kiezen
btn_output = tk.Button(f3, text="Uitvoer", font="bold", command=open_output_file, width=10, height=2)
btn_output.grid(row=0, column=0, sticky=tk.E, pady=2, padx=2)

# Tekstveld dat het pad van het uitvoerbestand toont.
# state="readonly": gebruiker kan niet typen, enkel lezen.
# textvariable=output_file: het veld updatet automatisch wanneer output_file wijzigt.
txt_output = tk.Entry(f4, textvariable=output_file, relief="sunken", width=70,
                      state="readonly", readonlybackground="lightyellow")
txt_output.grid(row=0, column=0, sticky="new", pady=2, padx=2)
# Rechtermuisklik-menu aan het tekstveld koppelen
txt_output.bind("<Button-3>", lambda event: show_context_menu(event, txt_output))


# =============================================================================
# WIDGETS: CONVERTEERKNOP (f5 / f6)
# =============================================================================
# De knop roept run_conversie() op. Na klikken wordt hij uitgeschakeld
# tot de verwerking klaar is, zodat de gebruiker niet twee keer klikt.
# -----------------------------------------------------------------------------
btn_run = tk.Button(f6, text="Converteer", font="bold", command=run_conversie, width=15, height=2)
btn_run.grid(row=0, column=0, sticky=tk.E, pady=2, padx=2)


# =============================================================================
# WIDGETS: STATUSLABEL (f7 / f8)
# =============================================================================
# Het label toont de voortgang tijdens de conversie (bijv. "Bezig... 3/10")
# en het eindresultaat ("Klaar! 10/10 PDF's omgezet.").
# textvariable=status_var: het label updatet automatisch wanneer status_var
# gewijzigd wordt, ook vanuit de achtergrond-thread (via root.after).
# -----------------------------------------------------------------------------
lbl_status = tk.Label(
    f8,
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
