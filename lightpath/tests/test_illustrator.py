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


def test_draw_beam(mps_path):
    i = Illustrator()
    l = i.draw_path(mps_path)
    assert len(l.widgets) == 2*len(mps_path.devices)-1


