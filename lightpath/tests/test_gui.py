############
# Standard #
############
import os.path

###############
# Third Party #
###############
import pytest

##########
# Module #
##########
from lightpath.ui import LightApp

def test_app_buttons(lcls):
    lightapp = LightApp(*lcls)
    #Check we initialized correctly
    assert lightapp.upstream()
    #Create widgets
    assert len(lightapp.select_devices('MEC')) == 10
    #Setup new display
    mec_idx = lightapp.destination_combo.findText('MEC')
    lightapp.destination_combo.setCurrentIndex(mec_idx)
    lightapp.change_path_display()
    assert len(lightapp.rows) == 10

def test_beampath_controls(lcls):
    lightapp = LightApp(*lcls)
    lightapp.remove(True, device=lightapp.rows[0].device)
    assert lightapp.rows[0].device.removed
    lightapp.insert(True, device=lightapp.rows[0].device)
    assert lightapp.rows[0].device.inserted
    lightapp.transmission_adjusted(50)
    assert lightapp.path.minimum_transmission == 0.5
