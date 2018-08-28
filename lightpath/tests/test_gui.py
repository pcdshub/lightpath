from unittest.mock import Mock
from distutils.spawn import find_executable

from lightpath.ui import LightApp, LightRow
from lightpath.controller import LightController
from lightpath.tests.conftest import Crystal


def test_app_buttons(lcls_client):
    lightapp = LightApp(LightController(lcls_client))
    # Create widgets
    assert len(lightapp.select_devices('MEC')) == 10
    # Setup new display
    mec_idx = lightapp.destination_combo.findText('MEC')
    lightapp.destination_combo.setCurrentIndex(mec_idx)
    lightapp.change_path_display()
    assert len(lightapp.rows) == 10


def test_lightpath_launch_script():
    # Check that the executable was installed
    assert find_executable('lightpath')


def test_focus_on_device(lcls_client, monkeypatch):
    lightapp = LightApp(LightController(lcls_client))
    row = lightapp.rows[8][0]
    monkeypatch.setattr(lightapp.scroll,
                        'ensureWidgetVisible',
                        Mock())
    # Grab the focus
    lightapp.focus_on_device(name=row.device.name)
    lightapp.scroll.ensureWidgetVisible.assert_called_with(row)
    # Go to impediment if no device is provided
    first_row = lightapp.rows[0][0]
    first_row.insert()
    lightapp.focus_on_device()
    lightapp.scroll.ensureWidgetVisible.assert_called_with(first_row)
    # Smoke test a bad device string
    lightapp.focus_on_device('blah')


def test_filtering(lcls_client, monkeypatch):
    lightapp = LightApp(LightController(lcls_client))
    monkeypatch.setattr(LightRow,
                        'setVisible',
                        Mock())
    # Hide Crystal devices
    lightapp.show_devicetype(False, Crystal)
    for row in lightapp.rows:
        if isinstance(row[0].device, Crystal):
            row[0].setVisible.assert_called_with(False)
    # Show Crystal devices
    lightapp.show_devicetype(True, Crystal)
    for row in lightapp.rows:
        if isinstance(row[0].device, Crystal):
            row[0].setVisible.assert_called_with(True)
    # Insert at least one device then hide
    device_row = lightapp.rows[2][0]
    device_row.device.insert()
    lightapp.show_removed(False)
    for row in lightapp.rows:
        if row[0].device.inserted:
            row[0].setVisible.assert_called_with(False)
    # Hide upstream devices
    lightapp.select_devices('MEC')
    lightapp.show_upstream(False)
    for row in lightapp.rows:
        if row[0].device.md.beamline != 'MEC':
            row[0].setVisible.assert_called_with(False)
