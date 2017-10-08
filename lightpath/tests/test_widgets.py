############
# Standard #
############
from unittest.mock import Mock

###############
# Third Party #
###############
import pytest
from PyQt5.QtWidgets import QApplication

##########
# Module #
##########
import lightpath.ui

@pytest.fixture(scope='function')
def lightrow(path):
    app = QApplication([])
    #Generate lightpath
    w = lightpath.ui.LightRow(path.path[3], path)
    #Replace Update functions with mocks
    setattr(w.state_label, 'setText', Mock())
    #setattr(w.indicator, 'update', Mock())
    return w

def test_widget_updates(lightrow):
    #Toggle device to trigger callbacks
    lightrow.device.remove()
    lightrow.device.insert()
    #Check that callbacks have been called
    assert lightrow.state_label.setText.called

