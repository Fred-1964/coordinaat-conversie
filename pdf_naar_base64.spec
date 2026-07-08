# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# PyInstaller spec-bestand voor pdf_naar_base64.py
# =============================================================================
# Bouwen met:  pyinstaller pdf_naar_base64.spec
# De exe verschijnt daarna in de map dist\
#
# Een spec-bestand is een Python-script dat PyInstaller uitvoert. Het
# beschrijft welke bestanden in de exe moeten en hoe die gebouwd wordt.
# =============================================================================

a = Analysis(
    ['pdf_naar_base64.py'],       # het hoofdscript dat gebouwd wordt
    pathex=[],
    binaries=[],
    # datas: extra (niet-Python) bestanden die mee in de exe verpakt worden.
    # Het icoon moet mee omdat root.iconbitmap() het bij het opstarten nodig
    # heeft; resource_path() vindt het dan terug via sys._MEIPASS.
    # ('bron', '.') betekent: plaats het bestand in de hoofdmap van de exe.
    datas=[('coordinaat_conversie.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pdf_naar_base64',       # naam van de exe: pdf_naar_base64.exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                     # exe comprimeren met UPX (indien geïnstalleerd)
    upx_exclude=[],
    runtime_tmpdir=None,
    icon='coordinaat_conversie.ico',  # icoon van het exe-bestand zelf (in Verkenner)
    console=False,                # geen zwart consolevenster naast de GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
