"""
Configuration for LCLS beamlines
"""
post_xrtm2h = 817.2
xpp_lodcm = 781.2

beamlines = {'XPP': {'HXD': {'end': xpp_lodcm}},
             'XCS': {'HXD': {}},
             'PBT': {'HXD': {'end': post_xrtm2h},
                     'XCS': {}},
             'MFX': {'HXD': {'end': post_xrtm2h}},
             'CXI': {'HXD': {}},
             'MEC': {'HXD': {'end': post_xrtm2h}}}
