############
# Standard #
############

###############
# Third Party #
###############

##########
# Module #
##########
from .conftest import requires_pedl

@requires_pedl
def test_light_widget():
    from lightpath.ui.widgets import LightWidget, PipeWidget
    import pedl
    lw = LightWidget('PV:BASE', 'name')

    #Check total widget layout
    assert isinstance(lw.widgets[0], pedl.StackedLayout)
    assert isinstance(lw.widgets[1], pedl.VBoxLayout)


@requires_pedl
def test_pipe_widget():
    from lightpath.ui.widgets import LightWidget, PipeWidget
    import pedl
    pw = PipeWidget('PV:LIGHT', 2, 3)
    assert len(pw.widgets) == 2
    assert all(isinstance(x, pedl.widgets.Rectangle)
               for x in pw.widgets)
