"""
Configuration for LCLS beamlines
"""
post_xrtm2h = 817.2
xpp_lodcm = 781.2

beamlines = {'XPP': {'LFE': {},
                     'HXD': {'end': xpp_lodcm}},
             'XCS': {'LFE': {},
                     'HXD': {}},
             'PBT': {'LFE': {},
                     'HXD': {'end': post_xrtm2h},
                     'XCS': {}},
             'MFX': {'LFE': {},
                     'HXD': {'end': post_xrtm2h}},
             'CXI': {'LFE': {},
                     'HXD': {}},
             'MEC': {'LFE': {},
                     'HXD': {'end': post_xrtm2h}},
             'TMO': {'KFE': {}},
             'RIX': {'KFE': {}},
             }
