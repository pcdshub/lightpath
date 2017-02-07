import pytest
import lightpath
from   lightpath import BeamPath

def test_start(beampath):
    assert beampath.start.z == 0.

def test_finish(beampath):
    assert beampath.finish.z == 30.

def test_range(beampath):
    assert beampath.range == (0.,30.)

def test_sort(beampath):
    for i,device in enumerate(beampath.devices):
        try:
            assert device.z < beampath.devices[i+1].z
        
        except IndexError:
            print('End of devices')

def test_reject_non_device():
    with pytest.raises(TypeError):
        BeamPath(5)

def test_reject_z_less_device(simple_device):
    simple_device._z = -1.0
    with pytest.raises(lightpath.errors.CoordinateError):
        bp = BeamPath(simple_device)


def test_mirror_finding(beampath, simple_mirror):
    assert beampath.mirrors  == [simple_mirror]

def test_device_names(beampath):
    assert 'one'     in beampath.device_names
    assert 'two'     in beampath.device_names
    assert 'three'   in beampath.device_names
    assert 'four'    in beampath.device_names
    assert 'five'    in beampath.device_names
    assert 'six'     in beampath.device_names
    assert 'simple' in beampath.device_names
    assert 'mirror'  in beampath.device_names
    assert 'complex' in beampath.device_names

def test_device_bases(beampath):
    assert 'DEVICE_1'  in beampath.device_prefixes
    assert 'DEVICE_2'  in beampath.device_prefixes
    assert 'DEVICE_3'  in beampath.device_prefixes
    assert 'DEVICE_4'  in beampath.device_prefixes
    assert 'DEVICE_5'  in beampath.device_prefixes
    assert 'DEVICE_6'  in beampath.device_prefixes
    assert 'SIMPLE'    in beampath.device_prefixes
    assert 'MIRROR'    in beampath.device_prefixes
    assert 'COMPLEX'   in beampath.device_prefixes

def test_clear_beamline(beampath):
    assert beampath.blocking_devices == []
    assert beampath.impediment == None
    assert beampath.cleared == False
