# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller-spec voor de MAC-versie van Coördinaat Conversie Batch.
#
# Bouwen kan alleen OP een Mac (PyInstaller kan niet "kruislings" bouwen):
#
#     pyinstaller coordinaat_conversie_batch_mac.spec --noconfirm
#
# Resultaat: dist/Coordinaat Conversie Batch.app
# Normaal doet GitHub Actions dit automatisch (.github/workflows/build-mac.yml).
#
# Verschillen met de Windows-spec (coordinaat_conversie_batch.spec):
#
#  - ONEDIR i.p.v. ONEFILE. De Windows-exe is één bestand dat zichzelf bij elke
#    start uitpakt in een tijdelijke map. Een Mac-app IS al een map (de
#    .app-"bundel"), dus daar zetten we alles gewoon uitgepakt in. Daardoor
#    start de app veel sneller. Dit zijn de stappen EXE -> COLLECT -> BUNDLE.
#  - BUNDLE maakt van de map een echte .app met icoon en Info.plist.
#  - target_arch='arm64' = Apple Silicon (M1, M2, M3, M4).
#  - upx=False: UPX-compressie werkt niet op Apple Silicon en maakt de
#    verplichte code-ondertekening ongeldig.
#  - Het .ico-bestand hoeft niet in 'datas': het Mac-script gebruikt het niet.
#    Het icoon (.icns) wordt door BUNDLE in de app gezet.


a = Analysis(
    ['coordinaat_conversie_batch_mac.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    [],
    exclude_binaries=True,          # binaries komen in COLLECT (onedir)
    name='coordinaat_conversie_batch_mac',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                  # geen Terminal-venster
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',            # Apple Silicon
    codesign_identity=None,         # None = "ad-hoc" ondertekening (zie README)
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='coordinaat_conversie_batch_mac',
)

# BUNDLE wordt alleen op macOS uitgevoerd; op andere systemen slaat
# PyInstaller deze stap over.
app = BUNDLE(
    coll,
    name='Coordinaat Conversie Batch.app',
    icon='coordinaat_conversie.icns',
    bundle_identifier='be.coordinaatconversie.batch',
    version='1.0.0',
    info_plist={
        # Naam zoals de Mac die toont (hier mag de ö wel in)
        'CFBundleDisplayName': 'Coördinaat Conversie Batch',
        # Scherpe weergave op Retina-schermen
        'NSHighResolutionCapable': True,
        # False = de app mag de donkere modus van macOS volgen
        'NSRequiresAquaSystemAppearance': False,
    },
)
