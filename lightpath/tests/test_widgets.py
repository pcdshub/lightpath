from unittest.mock import Mock

import pytest

import lightpath.ui
from lightpath.ui.widgets import state_colors, to_stylesheet_color

@pytest.fixture(scope='function')
def lightrow(path):
    # Generate lightpath
    w = lightpath.ui.LightRow(path.path[3])
    # Replace Update functions with mocks
    setattr(w.state_label, 'setText', Mock())
    return w


def test_widget_updates(lightrow):
    # Toggle device to trigger callbacks
    lightrow.device.remove()
    assert (to_stylesheet_color(state_colors[0])
            in lightrow.state_label.styleSheet())
    assert lightrow.insert_button.isEnabled()
    assert not lightrow.remove_button.isEnabled()
    lightrow.device.insert()
    assert not lightrow.insert_button.isEnabled()
    assert lightrow.remove_button.isEnabled()
    assert (to_stylesheet_color(state_colors[1])
            in lightrow.state_label.styleSheet())
    # Check that callbacks have been called
    assert lightrow.state_label.setText.called


def test_widget_controls(lightrow):
    lightrow.remove()
    assert lightrow.device.removed
    lightrow.insert()
    assert lightrow.device.inserted
