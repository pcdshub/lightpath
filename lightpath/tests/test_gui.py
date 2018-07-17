from distutils.spawn import find_executable

from lightpath.ui import LightApp
from lightpath.controller import LightController


def test_app_buttons(lcls_client):
    lightapp = LightApp(LightController(lcls_client))
    # Check we initialized correctly
    assert lightapp.upstream()
    # Create widgets
    assert len(lightapp.select_devices('MEC')) == 10
    # Setup new display
    mec_idx = lightapp.destination_combo.findText('MEC')
    lightapp.destination_combo.setCurrentIndex(mec_idx)
    lightapp.change_path_display()
    assert len(lightapp.rows) == 10


def test_beampath_controls(lcls_client):
    lightapp = LightApp(LightController(lcls_client))
    lightapp.transmission_adjusted(50)
    assert lightapp.path.minimum_transmission == 0.5


def test_lightpath_launch_script():
    # Check that the executable was installed
    assert find_executable('lightpath')
