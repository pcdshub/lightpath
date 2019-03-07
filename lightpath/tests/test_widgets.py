from unittest.mock import Mock

from ophyd import Device
import pytest

import lightpath.ui
from lightpath.ui.widgets import (state_colors, to_stylesheet_color,
                                  symbol_for_device)


@pytest.fixture(scope='function')
def lightrow(path, qapp, qtbot):
    # Generate lightpath
    w = lightpath.ui.LightRow(path.path[3])
    qtbot.addWidget(w)
    # Replace Update functions with mocks
    setattr(w.state_label, 'setText', Mock())
    return w


def test_widget_updates(lightrow):
    # Toggle device to trigger callbacks
    lightrow.device.remove()
    assert (to_stylesheet_color(state_colors[0])
            in lightrow.state_label.styleSheet())
    lightrow.device.insert()
    assert (to_stylesheet_color(state_colors[1])
            in lightrow.state_label.styleSheet())
    # Check that callbacks have been called
    assert lightrow.state_label.setText.called


def test_widget_icon(lightrow):
    assert symbol_for_device(lightrow.device) == lightrow.device._icon
    # Smoke test a device without an icon
    device = Device(name='test')
    symbol_for_device(device)
    # Smoke test a device with a malformed icon
    device._icon = 'definetly not an icon'
    lr = lightpath.ui.LightRow(device)
    lr.update_state()


def test_widget_hints(lightrow):
    hint_count = len(lightrow.device.hints['fields'])
    # Check for label and control for each hint plus spacer
    assert lightrow.command_layout.count() == 2 * hint_count + 1
