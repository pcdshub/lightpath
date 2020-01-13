from unittest.mock import Mock
from distutils.spawn import find_executable

from lightpath.ui import LightApp
from lightpath.controller import LightController


def test_app_buttons(lcls_client, qtbot):
    lightapp = LightApp(LightController(lcls_client))
    qtbot.addWidget(lightapp)
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


def test_focus_on_device(lcls_client, monkeypatch, qtbot):
    lightapp = LightApp(LightController(lcls_client))
    qtbot.addWidget(lightapp)
    row = lightapp.rows[8][0]
    monkeypatch.setattr(lightapp.scroll,
                        'ensureWidgetVisible',
                        Mock())
    # Grab the focus
    lightapp.focus_on_device(name=row.device.name)
    lightapp.scroll.ensureWidgetVisible.assert_called_with(row)
    # Go to impediment if no device is provided
    first_row = lightapp.rows[0][0]
    first_row.device.insert()
    lightapp.focus_on_device()
    lightapp.scroll.ensureWidgetVisible.assert_called_with(first_row)
    # Smoke test a bad device string
    lightapp.focus_on_device('blah')


def test_filtering(lcls_client, monkeypatch, qtbot):
    lightapp = LightApp(LightController(lcls_client))
    qtbot.addWidget(lightapp)
    # Create mock functions
    for row in lightapp.rows:
        monkeypatch.setattr(row[0], 'setHidden', Mock())
    # Initialize properly with nothing hidden
    lightapp.filter()
    for row in lightapp.rows:
        row[0].setHidden.assert_called_with(False)
    # Insert at least one device then hide
    device_row = lightapp.rows[2][0]
    device_row.device.insert()
    lightapp.remove_check.setChecked(False)
    lightapp.upstream_check.setChecked(True)
    # Reset mock
    for row in lightapp.rows:
        row[0].setHidden.reset_mock()
    lightapp.filter()
    for row in lightapp.rows:
        if row[0].device.removed:
            row[0].setHidden.assert_called_with(True)
        else:
            row[0].setHidden.assert_called_with(False)
    # Hide upstream devices
    lightapp.select_devices('MEC')
    lightapp.remove_check.setChecked(True)
    lightapp.upstream_check.setChecked(False)
    lightapp.filter()
    for row in lightapp.rows:
        if row[0].device.md.beamline != 'MEC':
            row[0].setHidden.assert_called_with(True)
        else:
            row[0].setHidden.assert_called_with(False)
    # Dual hidden categories will not fight
    lightapp.remove_check.setChecked(False)
    lightapp.filter()
    for row in lightapp.rows:
        if row[0].device.md.beamline != 'MEC' or row[0].device.removed:
            row[0].setHidden.assert_called_with(True)
        else:
            row[0].setHidden.assert_called_with(False)


def test_typhos_display(lcls_client, qtbot):
    lightapp = LightApp(LightController(lcls_client))
    qtbot.addWidget(lightapp)
    # Smoke test the hide button without a detailed display
    lightapp.hide_detailed()
    assert lightapp.detail_layout.count() == 2
    assert lightapp.device_detail.isHidden()
    lightapp.show_detailed(lightapp.rows[0][0].device)
    assert lightapp.detail_layout.count() == 3
    assert not lightapp.device_detail.isHidden()
    # Smoke test the hide button without a detailed display
    lightapp.hide_detailed()
    assert lightapp.detail_layout.count() == 2
    assert lightapp.device_detail.isHidden()
