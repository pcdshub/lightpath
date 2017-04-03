import pytest
from unittest.mock import Mock

from ophyd import Component
from ophyd.signal import Signal

import lightpath



def test_fault(mps):
    mps.alarm.put(2)
    assert mps.faulted


def test_bypass(mps):
    assert not mps.bypassed
    mps.bypass.put(1)
    assert mps.bypassed
    mps.alarm.put(2)
    assert not mps.faulted
    mps.bypass.put(0)
    assert mps.faulted


def test_veto(mps):
    mps._veto = True
    assert mps.veto_capable


def test_fault_callback(mps):
    m = Mock()
    mps.subscribe(m, event_type=mps.SUB_MPS,  run=False)
    mps.alarm.put(2)
    assert m.called


def test_bypass_callback(mps):
    m = Mock()
    mps.subscribe(m,event_type=mps.SUB_MPS, run=False)
    mps.bypass.put(0)
    assert m.called


def test_path_faults(mps_path):
    assert mps_path.faulted_devices == []
    d = mps_path.devices[1]
    d.insert()
    assert mps_path.faulted_devices == [d]

def test_veto_device(mps_path):
    assert mps_path.veto_devices == [mps_path.devices[0], mps_path.devices[2]]

def test_bad_insert(mps_path):
    with pytest.raises(lightpath.errors.MPSFault):
        mps_path.insert('mps_1')

    mps_path.insert('mps_1', force=True)
    assert mps_path.devices[1].inserted


def test_bad_remove(mps_path):
    [d.insert() for d in mps_path.devices]
    with pytest.raises(lightpath.errors.MPSFault):
        mps_path.remove('veto_1')
    mps_path.remove('mps_1')
    mps_path.remove('veto_1')
    assert mps_path.devices[0].removed

def test_double_veto(mps_path):
    [d.insert() for d in mps_path.devices]
    mps_path.remove('mps_1')
    mps_path.remove('veto_2', force=True)
    assert mps_path.devices[2].removed
    with pytest.raises(lightpath.errors.MPSFault):
        mps_path.remove('veto_1')

    mps_path.insert('veto_2')
    mps_path.remove('veto_1')
    assert mps_path.devices[0].removed
