####################
# Standard Library #
####################
import io
from collections import OrderedDict

####################
#    Third Party   #
####################
import pytest
from unittest.mock import Mock

####################
#     Package      #
####################
import lightpath
from lightpath import BeamPath
from .conftest import Crystal

def test_range(path):
    assert path.range == (0.,30.)


def test_sort(path):
    for i,device in enumerate(path.path):
        try:
        #Each devices is before than the next
            assert device.z < path.path[i+1].z
        #Except for the final device
        except IndexError:
            assert i == len(path.devices) - 1

def test_branching_finding(path):
    #Find the optic along the beampath
    assert len(path.branching) == 1
    assert isinstance(path.branching[0], Crystal)


def test_clear_beamline(path, branch):
    #Completely removed beamline
    assert path.blocking_devices == []
    assert path.impediment == None
    assert path.cleared

    #Passive device inserted
    path.path[6].insert()
    assert path.blocking_devices == []
    assert path.impediment == None
    assert path.cleared

    #Branch with optic inserted
    branch.path[5].insert() 
    assert branch.blocking_devices == []
    assert branch.incident_devices == [branch.path[5]]
    assert branch.impediment == None
    assert branch.cleared


def test_single_impediment(path, branch):
    #Insert generic device
    path.path[0].insert()
    assert path.impediment.name  == 'one'
    assert path.blocking_devices == [path.impediment]
    assert path.incident_devices == [path.impediment]
    assert path.cleared == False
    path.path[0].remove()
    
    #Insert passive device
    path.path[6].insert()
    assert path.impediment.name  == 'six'
    assert path.blocking_devices == None
    assert path.incident_devices == [path.path[6]]
    assert path.cleared == True
    path.path[6].remove()
   
    #Insert blocking optic
    path.path[5].insert()
    assert path.impediment.name  == 'five'
    assert path.blocking_devices == [path.impediment]
    assert path.incident_devices == [path.impediment]
    assert path.cleared == False
    path.path[5].remove()
   
    #Removed neccesary optic
    assert branch.impediment.name  == 'five'
    assert branch.blocking_devices == [branch.impediment]
    assert branch.incident_devices == [branch.impediment]
    assert branch.cleared == False


def test_multiple_insert_beamline(path):
    #Insert two devices
    path.path[1].insert()
    path.path[3].insert()
    #Assert we have the proper stopping point
    assert path.impediment.z == 2.0
    #Assert both are accounted reported
    assert len(path.blocking_devices) == 2

def test_show_device(path):
    #Write table to file-like object
    f = io.StringIO()
    path.show_devices(file=f)
    #Read from start of document
    f.seek(0)
    assert f.read() == known_table

known_table = """\
+---------+----------+----------+----------+------------+
| Name    | Prefix   | Position | Beamline |      State |
+---------+----------+----------+----------+------------+
| one     | DEVICE_1 |  0.00000 |     LCLS |  'removed' |
| two     | DEVICE_2 |  2.00000 |     LCLS |  'removed' |
| simple  | SIMPLE   |        4 |     LCLS |  'removed' |
| three   | DEVICE_3 |  9.00000 |     LCLS |  'removed' |
| complex | COMPLEX  |       10 |     LCLS |  'removed' |
| four    | DEVICE_4 | 15.00000 |     LCLS |  'removed' |
| mirror  | MIRROR   | 15.50000 |     LCLS | 'inserted' |
| five    | DEVICE_5 | 16.00000 |      HXR |  'removed' |
| six     | DEVICE_6 | 30.00000 |      HXR |  'removed' |
+---------+----------+----------+----------+------------+
"""


def test_ignore(beampath, complex_device, simple_device, simple_mirror):
    target, ignore = beampath._ignore(simple_device, passive=False)
    assert ignore == [simple_mirror, simple_device]
    should_target = [d for d in beampath.devices
                     if d not in [simple_mirror,simple_device]]
    assert should_target == target
    target, ignore = beampath._ignore([complex_device, simple_device])
    assert ignore == [simple_mirror, complex_device, simple_device]
    should_target.remove(complex_device)
    assert target == should_target


def test_clear(beampath, simple_mirror):
    dev = beampath.devices[3]
    dev.insert()
    dev = beampath.devices[2]
    dev.insert()
    dev = beampath.devices[7]
    dev.insert()
    status = beampath.clear(wait=True, timeout=1.)
    assert beampath.cleared
    assert beampath.output == ('HXR',  1.)

    assert all([lambda s : s.done for s in status])

def test_join(simple_device, simple_mirror, complex_device):
    bp1 = BeamPath(simple_device)
    bp2 = BeamPath(simple_mirror, complex_device)
    bp  = BeamPath(simple_device, simple_mirror, complex_device)

    assert BeamPath.from_join(bp1, bp2) == bp
    assert bp1.join(bp2) == bp
    assert bp2.join(bp1) == bp

    with pytest.raises(TypeError):
        bp1.join(4)

def test_split(simple_device, simple_mirror, complex_device):
    bp1 = BeamPath(simple_device)
    bp2 = BeamPath(simple_mirror, complex_device)
    bp  = BeamPath(simple_device, simple_mirror, complex_device)
    assert bp.split(device=complex_device) == (bp1, bp2)
    assert bp.split(z=10) == (bp1, bp2)


    with pytest.raises(ValueError):
        bp1.split()

    with pytest.raises(ValueError):
        bp1.split(400)


def test_callback(path):
    cb = Mock()
    beampath.subscribe(cb, event_type=beampath.SUB_PTH_CHNG, run=False)
    beampath.devices[4].insert()
    assert cb.called

