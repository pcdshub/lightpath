############
# Standard #
############

###############
# Third Party #
###############
import pedl

##########
# Module #
##########
from lightpath.ui.widgets import LightWidget, PipeWidget


def test_light_widget():
    lw = LightWidget('PV:BASE', 'name')

    #Check total widget layout
    assert isinstance(lw.widgets[0], pedl.widgets.Rectangle)
    assert isinstance(lw.widgets[1], pedl.VBoxLayout)


def test_pipe_widget():
    pw = PipeWidget('PV:LIGHT', 2)
    assert len(pw.widgets) == 2
    assert all(isinstance(x, pedl.widgets.Rectangle)
               for x in pw.widgets)
