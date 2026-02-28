#import libraries
import tkinter as tk
from tkinter.ttk import Combobox
import pandas as pd
import  tkinter.messagebox
from tkinter import filedialog
from tkinter import StringVar
import os
import sys
from pyproj import Transformer
from  pathlib import Path
from shapely.geometry import Polygon

# pad naar icoon werkt zowel als script als als PyInstaller exe
def resource_path(filename):
    base = getattr(sys, '_MEIPASS', Path(__file__).parent)
    return Path(base) / filename


#initialisatie tkinter form
root = tk.Tk()
root.geometry('570x800')
root.title("Coördinaat Converter")
root.resizable(True, True)
root.iconbitmap(resource_path("coordinaat_conversie.ico"))
#extra code om tekstvelden mee te vergroten met formulier
root.grid_columnconfigure(1,weight=1)
root.grid_rowconfigure(4,weight=1)

#Initialisatie  globale tkinter formulier variabelen en instellen standaard waarde
input_file = StringVar()
input_file.set("")
input_preview = StringVar()
input_preview.set("")
output_file = StringVar()
output_file.set("")
lst_conversies_input = ('L72', 'UTM31', 'WGS84','L2008')
lst_conversies_output = ('L72', 'UTM31', 'WGS84','L2008')
lst_separator_input = ('komma(decimaal punt)','spatie(decimaal punt)','tab(decimaal punt)','punt-komma(decimaal komma)',
                       'punt-komma(decimaal punt)')
lst_separator_output = ('komma(decimaal punt)','spatie(decimaal punt)','tab(decimaal punt)','punt-komma(decimaal komma)',
                        'punt-komma(decimaal punt)')

# dictionary met waarden, key label coordmodel, value de CRS code
# key waarde is gelijk aan de waardes die in de dropdown input coord voorkomt
CRS_CODES = {
    "L72": "EPSG:31370",
    "UTM31": "EPSG:32631",
    "WGS84": "EPSG:4326",
    "L2008": "EPSG:3812",
}

# dictionary met de headers outputfile, key waardes zijn gelijk aan inhoud uit dropdown, tuple de kolomkoppen van het outputfile
HEADERS = {

    "L72": ("x_L72", "y_L72"),
    "UTM31": ("x_UTM31", "y_UTM31"),
    "WGS84": ("LAT", "LON"),
    "L2008": ("x_L2008", "y_L2008"),
}

diepte_switch = tk.BooleanVar()
diepte_switch.set(False)
header_input_switch = tk.BooleanVar()
header_input_switch.set(False)
header_output_switch = tk.BooleanVar()
header_output_switch.set(True)
eerste_kolom_naam_switch = tk.BooleanVar()
eerste_kolom_naam_switch.set(False)
reductievlak_conversie_keuze = tk.IntVar()
reductievlak_conversie_keuze.set(0)
reductievlak_waarde = tk.IntVar()
reductievlak_waarde.set(0)
status_var = tk.StringVar()
status_var.set("")

def scheidingsteken_ophalen():
    #scheidingsteken uit dropdown input coord halen.
    #hier gebruik gemaakt van een dictionary
    input_separators = {
        'komma(decimaal punt)': (",", "."),
        'spatie(decimaal punt)': (" ", "."),
        'tab(decimaal punt)': ("\t", "."),
        'punt-komma(decimaal komma)':(";", ","),
        'punt-komma(decimaal punt)': (";", ".")
    }

    separator, decimal = input_separators[combo_separator_in.get()]#variabelen scheidingsteken

    return separator,decimal

def scheidingsteken_geven():
    #scheidingsteken uit dropdown output coord.
    #als selctie wordt er gebruik gemaakt van een dictionary
    output_separators = {
        'komma(decimaal punt)': (",", "."),
        'spatie(decimaal punt)': (" ", "."),
        'tab(decimaal punt)': ("\t", "."),
        'punt-komma(decimaal komma)': (";", ","),
        'punt-komma(decimaal punt)': (";", ".")
    }
    separator, decimal = output_separators[combo_separator_out.get()]
    return separator, decimal

def preview(input_file):#functie om preview in put in tekstveld te zetten
    with open(input_file, "r") as f:
        coord = [lijn.strip() for lijn in f if lijn.strip()]  # sla enkel lege regels over
    input_preview.set("\n".join(coord[:5]))

def update_preview(*args):#functie om tekstveld geupdate houden
    txt_input_file.config(state="normal")
    txt_input_file.delete("1.0", tk.END)
    txt_input_file.insert("1.0", input_preview.get())
    txt_input_file.config(state="disabled")

input_preview.trace_add("write", update_preview)#code om tekstveld geupdate te houden

def dataFrame_inlezen(input_file):
    separator, decimal = scheidingsteken_ophalen()#functie oproepen scheidinsteken input

    if header_input_switch.get():#Gaat na of checkbox header aanstaat
        df = pd.read_csv(input_file, delimiter=separator, decimal=decimal, header=None, skiprows=1)
    else:
        df = pd.read_csv(input_file, delimiter=separator, decimal=decimal, header=None)

    return df

def cgp_to_dataframe(filename: str) -> pd.DataFrame:
    #functie om van *.cgp bestand dataFrame te maken
    with open(filename, "r", encoding="utf-8") as f:
        lines = [line.strip().replace("=", ",") for line in f if line.strip()]

    lines = lines[1:]

    df = pd.DataFrame([line.split(",") for line in lines])

    df.iloc[:,0] =df.iloc[:, 0].str.replace(" ","", regex=False)

    return df

def depth_toggle(df):
    # toggle functie negatieve diepte waarde naar positieve
    df['Z'] *= -1
    return df

def lat_to_taw(df):
    #functie om postcalculatie te doen om TAW-LAT correctie uit te voeren.
    #de key waarden komen de globale integervariabele waar keuze checkbox inzit
    #waardes worden in dictionary gezet
    conversie_waardes = {
        0: 0.69,
        1: 0.72,
        2: 0.73,
        3: 0.74,
        4: 0.75,
        5: 0.70,
        6: 0.25
    }

    conversie_waarde = conversie_waardes[reductievlak_waarde.get()]#in dictionary geselecteerde waarde naar variabele

    if reductievlak_conversie_keuze.get() == 1:
        df['Z'] -= conversie_waarde#uit dictionary gehaalde waarde bij Z waarde calculeren
    elif reductievlak_conversie_keuze.get() == 2:
        df['Z'] += conversie_waarde

    return df

def conversie(input_file, output_file):
    cgp_bestand = Path(input_file)#functie om dataFrame uit cgp functie te halen
    wkt_bestand = Path(output_file)

    if cgp_bestand.suffix == ".cgp":
        #als bestand *.cgp is wordt het dataFrame hiermee gemaakt.
        df = cgp_to_dataframe(input_file)
    else:
        #als input bestand geen *.cgp is wordt dataFrame gemaakt met andere opties (*.txt, *.asc, *.pts, enz,..)
        df = dataFrame_inlezen(input_file)

    aantal_kolommen = len(df.columns)#aantal kolomen DataFrame

    separator, decimal = scheidingsteken_geven()#scheidings teken output (opgehaald met functie)

    coord_in = CRS_CODES[combo_conv_in.get()]#input variabele om conversie te doen
    coord_out = CRS_CODES[combo_conv_out.get()]#output variabele om conversie te doen
    x_header, y_header = HEADERS[combo_conv_out.get()]#variabele met de headers outputfile

    transform_to_output = Transformer.from_crs(coord_in, coord_out, always_xy=True)#de eigenlijke conversie van het ene naar het
                                                                                   #andere coordstelsel

    #waarden worden naargelang het aantal kolommen in een nieuw dataFrame gezet
    if not eerste_kolom_naam_switch.get():
        x_output, y_output = transform_to_output.transform(df[0].values, df[1].values)
    else:
        x_output, y_output = transform_to_output.transform(df[1].values, df[2].values)

    if aantal_kolommen == 2:
        df_output = pd.DataFrame({x_header: x_output, y_header: y_output})
    elif aantal_kolommen == 3:
        if not eerste_kolom_naam_switch.get():
            df_output = pd.DataFrame({x_header: x_output, y_header: y_output, 'Z': df[2]})
        else:
            df_output = pd.DataFrame({'point': df[0], x_header: x_output, y_header: y_output})
    elif aantal_kolommen == 4:
        if not eerste_kolom_naam_switch.get():
            df_output = pd.DataFrame({x_header: x_output, y_header: y_output, 'Z': df[2], 'VAR': df[3]})
        else:
            df_output = pd.DataFrame({'point': df[0], x_header: x_output, y_header: y_output, 'Z': df[3]})
    else:
        raise ValueError(f"Onverwacht aantal kolommen: {aantal_kolommen}. Maximum is 4.")

    #ronde de getallen in het dataFrame af, wordt rekening gehouden met 6 decimalen bij wgs84
    if combo_conv_out.get() == "WGS84":
        df_output[x_header] = df_output[x_header].round(6)
        df_output[y_header] = df_output[y_header].round(6)
    else:
        df_output[x_header] = df_output[x_header].round(2)
        df_output[y_header] = df_output[y_header].round(2)

    if wkt_bestand.suffix == ".wkt":
        df_output = df_output.iloc[:, [1, 2]]
        coords = list(df_output.itertuples(index=False, name=None))
        poly = Polygon(coords)
        with open(output_file, 'w') as f:
            f.write(poly.wkt)
        return

    if 'Z' in df_output.columns:
        df_output['Z'] = df_output['Z'].round(2)

    if 'Z' in df_output.columns:
        if diepte_switch.get():
            df_output = depth_toggle(df_output)

    if reductievlak_conversie_keuze.get() != 0:
        #indien er reductievlak correctie nodig wordt dit hier uitgevoerd
        df_output = lat_to_taw(df_output)
        df_output['Z'] = df_output['Z'].round(2)

    if header_output_switch.get():
        #naargelang checkbox al dan niet een header in de output
        df_output.to_csv(output_file, index=False, sep=separator, decimal=decimal, header=True)
    else:
        df_output.to_csv(output_file, index=False, sep=separator, decimal=decimal, header=False)

def run(open_na_conversie=False):
    try:
        status_var.set("Bezig met conversie...")
        root.update_idletasks()
        conversie(input_file.get(), output_file.get())
        status_var.set("Klaar!")
        if open_na_conversie:
            os.startfile(output_file.get())
    except Exception as e:
        tkinter.messagebox.showerror('Foutje', f'Er zit iets mis!\n\n{e}')
        status_var.set("")

def open_file():
    #functie voor selectie input file
    status_var.set("")
    input_file.set(filedialog.askopenfilename(filetypes=[('txt Bestanden', '.txt'),
                                                           ('xyz Bestanden', '.xyz'), ('pts Bestanden', '.pts'),
                                                           ('csv Bestanden', '.csv'), ('asc Bestanden', '.asc'),
                                                           ('cgp Bestanden', '.cgp'), ('All Files', '.*')]))

    preview(input_file.get())



def save_file():
    #functie voor selectie outputfile
    status_var.set("")
    output_file.set(filedialog.asksaveasfilename(filetypes=[('asc Bestanden', '.asc'),
                                                              ('xyz Bestanden', '.xyz'),
                                                            ('wkt Bestanden', '.wkt'),
                                                              ('All Files', '.*')],
                                                   defaultextension='.asc'))

def show_context_menu(event, entry_widget):
    #context menu voor textboxen
    context_menu = tk.Menu(root, tearoff=0)

    context_menu.add_command(
        label="Knippen",
        command=lambda: entry_widget.event_generate("<<Cut>>")
    )
    context_menu.add_command(
        label="Kopiëren",
        command=lambda: entry_widget.event_generate("<<Copy>>")
    )
    context_menu.add_command(
        label="Plakken",
        command=lambda: entry_widget.event_generate("<<Paste>>")
    )
    context_menu.tk_popup(event.x_root, event.y_root)

#opbouw basis formulier in rijen en kolommen
f1 = tk.Frame(root)
f1.grid(row=0, column=0, sticky=tk.NE,padx=2,pady=3)

f2 = tk.LabelFrame(root, relief="groove", text="Invoer Bestand", font="bolt")
f2.grid(row=0, column=1, sticky="nsew",padx=2,pady=3)
f2.grid_columnconfigure(0, weight=1)
f2.grid_rowconfigure(0, weight=1)

f3 = tk.Frame(root)
f3.grid(row=1, column=0, sticky=tk.NE,padx=2,pady=3)

f4 = tk.LabelFrame(root, relief="groove", text="Uitvoer Bestand", font="bolt")
f4.grid(row=1, column=1, sticky="new",padx=2,pady=5)
#code is nodig om tekstveld zich te laten uitrekken
f4.grid_columnconfigure(0, weight=1)
f4.grid_rowconfigure(0, weight=1)

f5 = tk.Frame(root)
f5.grid(row=2, column=0, sticky=tk.NW,padx=2,pady=3)

f6 = tk.LabelFrame(root, relief="groove", text="Reductievlak (LAT Negatief!!)")
f6.grid(row=2, column=1, sticky=tk.NW,padx=2,pady=3)

f7 = tk.Frame(root)
f7.grid(row=3, column=0, sticky=tk.NW,padx=2,pady=5)

f8 = tk.Frame(root)
f8.grid(row=3, column=1, sticky=tk.NW,padx=2,pady=3)

f9 = tk.Frame(root)
f9.grid(row=4, column=0, sticky=tk.NW,padx=2,pady=3)

f10 = tk.Frame(root)
f10.grid(row=4, column=1, sticky=tk.NW,padx=2,pady=3)

#opbouw knoppen, labels en textboxen
btn_input = tk.Button(f1, text="Invoer", command=open_file, font="bold", width=10, height=2)
btn_input.grid(row=0, column=0, sticky=tk.E, pady=2, padx=2)
txt_input = tk.Entry(f2, textvariable=input_file, relief="sunken",width=70, state="readonly",readonlybackground="lightyellow")
txt_input.grid(row=0, column=0, sticky="nsew", pady=2, padx=2)
txt_input.bind("<Button-3>", lambda event: show_context_menu(event, txt_input))

txt_input_file = tk.Text(f2, relief="sunken", width=70, height=5, bg="lightyellow", state="disabled")
txt_input_file.grid(row=1, column=0, sticky="nsew", pady=2, padx=2)
txt_input_file.config(state="normal")
txt_input_file.delete("1.0", tk.END)
txt_input_file.insert("1.0", input_preview.get())
txt_input_file.config(state="disabled")

combo_conv_in = Combobox(f2, values=lst_conversies_input, height=10, width=30)
combo_conv_in.grid(row=2, column=0, sticky=tk.W, pady=2, padx=2)
combo_conv_in.set('UTM31')

combo_separator_in = Combobox(f2, values=lst_separator_input, height=10, width=30)
combo_separator_in.grid(row=3, column=0, sticky=tk.W, pady=2, padx=2)
combo_separator_in.set('spatie(decimaal punt)')
checkbox_eerste_kolom = tk.Checkbutton(f2, text="Eerste kolom bevat point-id",
                             variable=eerste_kolom_naam_switch)
checkbox_eerste_kolom.grid(row=4, column=0, sticky=tk.W, pady=2, padx=2)
checkbox_header_input = tk.Checkbutton(f2, text="Negeer titelrij",
                             variable=header_input_switch)
checkbox_header_input.grid(row=5, column=0, sticky=tk.W, pady=2, padx=2)

btn_output = tk.Button(f3, text="Uitvoer", font="bold", command=save_file, width=10, height=2)
btn_output.grid(row=0, column=0, sticky=tk.E, pady=2, padx=2)
txt_output = tk.Entry(f4, textvariable=output_file, relief="sunken",width=70, state="readonly",readonlybackground="lightyellow")
txt_output.grid(row=0, column=0, sticky="new", pady=2, padx=2)
txt_output.bind("<Button-3>", lambda event: show_context_menu(event, txt_output))

combo_conv_out = Combobox(f4, values=lst_conversies_output, height=10, width=30)
combo_conv_out.grid(row=1, column=0, sticky=tk.W, pady=2, padx=2)
combo_conv_out.set('L72')

combo_separator_out = Combobox(f4, values=lst_separator_output, height=10, width=30)
combo_separator_out.grid(row=2, column=0, sticky=tk.W, pady=2, padx=2)
combo_separator_out.set('komma(decimaal punt)')
checkbox_header_output = tk.Checkbutton(f4, text="Titelrij toevoegen",
                             variable=header_output_switch)
checkbox_header_output.grid(row=4, column=0, sticky=tk.W, pady=2, padx=2)
checkbox_diepte_hoogte = tk.Checkbutton(f4, text="Wissel hoogte/diepte",
                             variable=diepte_switch)
checkbox_diepte_hoogte.grid(row=3, column=0, sticky=tk.W, pady=2, padx=2)

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

btn_run = tk.Button(f8, text="Converteer", font="bold", command=run, width=11, height=2)
btn_run.grid(row=0, column=0, sticky=tk.E, pady=2, padx=2)

btn_run_output = tk.Button(f8, text="Converteer en\nopen bestand", font="bold", command=lambda: run(open_na_conversie=True), width=11, height=2)
btn_run_output.grid(row=0, column=1, sticky=tk.E, pady=2, padx=2)

#label dat status van de conversie weergeeft
lbl_status = tk.Label(
    f10,
    textvariable=status_var,
    font=("TkDefaultFont", 15, "bold"),
    fg="#b30000",
    bg="#f2f2f2",
)
lbl_status.grid(row=0, column=0, sticky=tk.NW, pady=2, padx=2)

root.mainloop()