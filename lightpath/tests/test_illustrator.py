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
from lightpath.ui import Illustrator


def test_draw_beam(path):
    i = Illustrator()
    l = i.draw_path(path)
    assert len(l.widgets) == 2*len(path.devices)-1


