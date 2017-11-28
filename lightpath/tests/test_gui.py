############
# Standard #
############
import os.path

###############
# Third Party #
###############
import pytest
from pcdsdevices.sim.pv import using_fake_epics_pv

##########
# Module #
##########
from lightpath.ui import LightApp

def test_app_buttons(lcls, containers):
    lightapp = LightApp(*lcls, containers=containers)
    #Check we initialized correctly
    assert lightapp.upstream()
    assert not lightapp.mps_only()
    #Create widgets
    assert len(lightapp.select_devices('MEC')) == 11
    #Setup new display
    mec_idx = lightapp.destination_combo.findText('MEC')
    lightapp.destination_combo.setCurrentIndex(mec_idx)
    lightapp.change_path_display()
    assert len(lightapp.rows) == 11

def test_beampath_controls(lcls, containers):
    lightapp = LightApp(*lcls, containers=containers)
    lightapp.remove(True, device=lightapp.rows[0].device)
    assert lightapp.rows[0].device.removed
    lightapp.insert(True, device=lightapp.rows[0].device)
    assert lightapp.rows[0].device.inserted
    lightapp.transmission_adjusted(50)
    assert lightapp.path.minimum_transmission == 0.5

@using_fake_epics_pv
@pytest.mark.xfail
def test_app_from_json():
    #Basic configuration
    lit = LightApp.from_json(os.path.join(
                             os.path.dirname(os.path.abspath(__file__)),
                             'path.json'))
    assert len(lit.light.devices) == 16
    #Limit device search
    lit = LightApp.from_json(os.path.join(
                             os.path.dirname(os.path.abspath(__file__)),
                             'path.json'),
                             end=900.0)
    assert len(lit.light.devices) == 9
