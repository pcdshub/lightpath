"""
Configuration for LCLS beamlines
"""

# mapping of endstation to either:
# - a list of branch names
# - a mapping of branch names to final z position
beamlines = {'XPP_PINK': {'L0': 800},
             'XPP_MONO': ['L2'],
             'XCS': ['L3'],
             'MFX': ['L5'],
             'CXI': ['L0'],
             'MEC': ['L4'],
             'TMO': ['K4'],
             'CRIX': ['K1'],
             'QRIX': ['K2'],
             'TXI': ['K3', 'L1']}
sources = ['K0', 'L0']
