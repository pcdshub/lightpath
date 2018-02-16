from unittest.mock import Mock

import pytest

import lightpath.ui


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
    lightrow.device.insert()
    # Check that callbacks have been called
    assert lightrow.state_label.setText.called
