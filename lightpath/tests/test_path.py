import io
import pytest
from collections import OrderedDict
from unittest.mock import Mock

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

def test_reject_uncontiguous(simple_device, complex_device):
    simple_device._beamline='HDF'
    with pytest.raises(lightpath.errors.PathError):
        BeamPath(simple_device, complex_device)

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
    mirror = beampath.devices[6]
    assert beampath.blocking_devices == []
    assert beampath.impediment == None
    assert beampath.incident_devices == [mirror]
    assert beampath.cleared
    assert beampath.output == ('HXR',  1.)

def test_single_insert_beamline(beampath):
    dev = beampath.devices[4]
    mirror = beampath.devices[6]
    dev.insert()
    assert beampath.impediment == dev
    assert beampath.blocking_devices == [dev]
    assert beampath.incident_devices == [dev]
    assert beampath.cleared == False
    assert beampath.output == ('LCLS',  0.5)
    dev.remove()
    dev = beampath.devices[8]
    dev.insert()
    assert beampath.impediment == dev
    assert beampath.blocking_devices == [dev]
    assert beampath.incident_devices == [mirror, dev]
    assert beampath.cleared == False
    assert beampath.output == ('HXR',  0.)

def test_multiple_insert_beamline(beampath):
    dev = beampath.devices[1]
    dev.insert()
    dev2 = beampath.devices[3]
    dev2.insert()
    assert beampath.impediment == dev
    assert beampath.blocking_devices == [dev, dev2]
    assert beampath.cleared == False
    assert beampath.output == ('LCLS',  0.)

def test_mirror_out(beampath):
    dev = beampath.devices[6]
    dev.remove()
    assert beampath.impediment == dev
    assert beampath.blocking_devices == [dev]
    assert beampath.cleared == False
    assert beampath.output == ('LCLS',  0.)

def test_show_device(beampath):
    f = io.StringIO()
    beampath.show_devices(file=f)
    f.seek(0)
    assert f.read() == known_table

    f = io.StringIO()
    beampath.show_devices(file=f, state='inserted')
    f.seek(0)
    assert f.read() == small_table

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

small_table="""\
+--------+--------+----------+----------+------------+
| Name   | Prefix | Position | Beamline |      State |
+--------+--------+----------+----------+------------+
| mirror | MIRROR | 15.50000 |     LCLS | 'inserted' |
+--------+--------+----------+----------+------------+
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



def test_lookup(beampath, simple_device):
    assert beampath._device_lookup(simple_device) == simple_device
    assert beampath._device_lookup('simple') == simple_device
    assert beampath._device_lookup('SIMPLE') == simple_device

    with pytest.raises(ValueError):
        beampath._device_lookup('NOT')

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

def test_configuration(simple_device, complex_device):
    bp = BeamPath(simple_device, complex_device)
    d = bp.read_configuration()
    assert 'simple' in d.keys()
    simple = d['simple']
    assert simple['state'] == 'removed'
    assert simple['config'] == OrderedDict()
    
    assert 'complex' in d.keys()
    cmplx = d['complex']
    assert cmplx['state'] == 'removed'
    assert cmplx['config']['complex_basic']['value'] == 4

def test_configuration_restore(simple_device, complex_device):
    bp      = BeamPath(simple_device, complex_device)
    initial = bp.read_configuration()
    bp.devices[0].insert()
    assert bp.devices[0].inserted
    bp.devices[1].basic.put(2)
    assert bp.devices[1].basic.get() == 2
    d = bp.read_configuration()
    
    assert 'simple' in d.keys()
    simple = d['simple']
    assert simple['state'] == 'inserted'
    assert simple['config'] == OrderedDict()

    assert 'complex' in d.keys()
    cmplx = d['complex']
    assert cmplx['state'] == 'removed'
    assert cmplx['config']['complex_basic']['value'] == 2

    bp.configure(initial)


    d = bp.read_configuration()
    assert 'simple' in d.keys()
    simple = d['simple']
    assert simple['state'] == 'removed'
    assert simple['config'] == OrderedDict()

    assert 'complex' in d.keys()
    cmplx = d['complex']
    assert cmplx['state'] == 'removed'
    print(cmplx)
    assert cmplx['config']['complex_basic']['value'] == 4


def test_unknown_configure(simple_device):
    simple_device.component.put(4)
    bp = BeamPath(simple_device)
    d = bp.read_configuration()
    bp.configure(d)
    assert simple_device.component.get() == 4
    simple_device.insert()
    bp.configure({'simple' : {'state' : 'unknown'}})
    assert simple_device.inserted


def test_insert_configure(simple_device):
    simple_device.insert()
    bp = BeamPath(simple_device)
    d = bp.read_configuration()
    simple_device.remove()
    bp.configure(d)
    assert simple_device.inserted


def test_callback(beampath):
    cb = Mock()
    beampath.subscribe(cb, event_type=beampath.SUB_PTH_CHNG, run=False)
    beampath.devices[4].insert()
    assert cb.called

