from unittest.mock import Mock

import pytest
from ophyd import Device
from pytestqt.qtbot import QtBot

from lightpath import BeamPath
from lightpath.ui import LightRow
from lightpath.ui.widgets import (state_colors, symbol_for_device,
                                  to_stylesheet_color)


@pytest.fixture(scope='function')
def lightrow(path: BeamPath, qtbot: QtBot):
    # Generate lightpath
    w = LightRow(path.path[3], path)
    qtbot.addWidget(w)
    # Replace Update functions with mocks
    setattr(w.state_label, 'setText', Mock())
    return w


def test_widget_updates(lightrow: LightRow, path: BeamPath, qtbot: QtBot):
    # inserted device may still permit beam
    ipimb = path.path[5]
    ipimb_row = LightRow(ipimb, path)
    # Insert valve downstream of ipimb
    valve10_row = LightRow(path.path[10], path)
    valve10_row.device.insert()
    # Toggle device to trigger callbacks
    ipimb.insert()
    ipimb.remove()
    ipimb.insert()

    # Valve3 (lightrow) and ipimb5 both inserted
    # minimum transmission = 0.1, fully blocked by valve3

    # expecting the device updated callback to trigger update in ipimb_row
    # half-removed == inserted but not in blocking devices
    def half_removed():
        return (to_stylesheet_color(state_colors['half_removed'])
                in ipimb_row.state_label.styleSheet())

    qtbot.waitUntil(half_removed, timeout=5)

    def valve10_blocking():
        return (to_stylesheet_color(state_colors['blocking'])
                in valve10_row.state_label.styleSheet())
    qtbot.waitUntil(valve10_blocking, timeout=5)

    lightrow.device.remove()

    def removed():
        return (to_stylesheet_color(state_colors['removed'])
                in lightrow.state_label.styleSheet())

    qtbot.waitUntil(removed, timeout=5)

    lightrow.device.insert()

    def blocking():
        return (to_stylesheet_color(state_colors['blocking'])
                in lightrow.state_label.styleSheet())

    qtbot.waitUntil(blocking, timeout=5)

    # Check that callbacks have been called
    assert lightrow.state_label.setText.called


def test_widget_icon(lightrow: LightRow):
    assert symbol_for_device(lightrow.device) == lightrow.device._icon
    # Smoke test a device without an icon
    device = Device(name='test')
    symbol_for_device(device)
    # Smoke test a device with a malformed icon
    device._icon = 'definetly not an icon'
    lr = LightRow(device, lightrow.path)
    lr.update_state()
