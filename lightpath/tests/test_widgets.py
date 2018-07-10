from unittest.mock import Mock

import pytest

import lightpath.ui
from lightpath.ui.widgets import state_colors


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
    assert state_colors[0] in lightrow.state_label.styleSheet()
    lightrow.device.insert()
    assert state_colors[1] in lightrow.state_label.styleSheet()
    # Check that callbacks have been called
    assert lightrow.state_label.setText.called
