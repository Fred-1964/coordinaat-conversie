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

root = tk.Tk()
root.geometry('570x800')
root.title("Batch Coördinaat Converter")
root.resizable(True, True)

root.mainloop()