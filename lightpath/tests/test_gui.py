############
# Standard #
############

###############
# Third Party #
###############
import pytest
from PyQt5.QtWidgets import QApplication

##########
# Module #
##########
from lightpath.ui import LightApp


@pytest.fixture(scope='function')
def lightapp(lcls):
    app = QApplication([])
    return LightApp(*lcls)


def test_app_buttons(lightapp):
    #Check we initialized correctly
    assert lightapp.upstream()
    assert not lightapp.mps_only()
    #Try to change display
    assert len(lightapp.select_devices('MEC')) == 10
