############
# Standard #
############

###############
# Third Party #
###############
import pytest

##########
# Module #
##########
from .conftest import requires_pedl

@requires_pedl
def test_draw_beam(path):
    from lightpath.ui.illustrator import Illustrator
    i = Illustrator()
    l = i.draw_path(path)
    assert len(l.widgets) == 2*len(path.devices)-1


