"""
Configuration for LCLS beamlines
"""

# mapping of endstation to branch name, (and possibly branch name to z end)
beamlines = {'XPP': {'L0': 800, 'L2': None},
             'XCS': ['L3'],
             'MFX': ['L5'],
             'CXI': ['L0'],
             'MEC': ['L4'],
             'TMO': ['K4'],
             'CRIX': ['K1'],
             'QRIX': ['K2'],
             'TXI': ['K3', 'L1']}
sources = ['K0', 'L0']
