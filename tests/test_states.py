#####
#####
import time
import pytest
import numpy as np
from unittest.mock import Mock
from ophyd.status  import wait

from lightpath.device import StateComponent, LightDevice
#####
#####


def test_simple_initial_state(simple_device):
    assert simple_device.state == 'removed'
    assert simple_device.removed
    assert not simple_device.blocking


def test_simple_insert(simple_device):
    simple_device.insert()
    assert simple_device.state == 'inserted'
    assert simple_device.blocking
    assert not simple_device.removed


def test_simple_remove(simple_device):
    simple_device.component.put(0)
    simple_device.remove()
    assert simple_device.state == 'removed'

def test_bad_transition(simple_device):
    simple_device.component.put(2)
    assert simple_device.state == 'unknown'


def test_unknown_transition(simple_device):
    simple_device.component.put(10)
    assert simple_device.state == 'unknown'

def test_complex_initial_state(complex_device):
    assert complex_device.state == 'removed'

def test_complex_insert(complex_device):
    complex_device.insert()
    assert complex_device.state == 'inserted'
    assert complex_device.inserted
    assert complex_device.blocking

def test_complex_remove(complex_device):
    complex_device.insert()
    complex_device.remove()
    assert complex_device.state == 'removed'

def test_complex_no_change(complex_device):
    complex_device.opn.put(4)
    complex_device.cls.put(4)
    assert complex_device.state == 'unknown'

def test_conflicting_states(complex_device):
    complex_device.opn.put(0)
    assert complex_device.state == 'unknown'
    assert complex_device.blocking

def test_unknown_states(complex_device):
    complex_device.opn.put(10)
    assert complex_device.blocking
    assert complex_device.state == 'unknown'

def test_simple_output(simple_device):
    assert simple_device.output == ('LCLS', 1.)
    simple_device.insert()
    assert simple_device.output == ('LCLS', 0.)
    simple_device.component.put(12)
    assert simple_device.output == ('LCLS', np.nan)

def test_passive(simple_device):
    simple_device._passive = True
    simple_device.insert()
    assert simple_device.output == ('LCLS', 1.)

def test_done_status(simple_device):
    status = simple_device._setup_move('removed')
    assert status.done

def test_not_done_status(simple_device):
    status = simple_device._setup_move(False)
    assert not status.done

def test_status_with_move(simple_device):
    status = simple_device._setup_move('inserted')
    simple_device.component.put(0)
    assert status.done
    assert status.success

def test_timeout_status(simple_device):
    status = simple_device._setup_move('inserted')

    with pytest.raises(TimeoutError):
        wait(status, timeout=0.05)

def test_callback_status(simple_device):
    
    cb = Mock()

    status = simple_device._setup_move('inserted',
                                       finished_cb=cb)
    simple_device.component.put(0)
    assert status.done
    assert status.success
    cb.assert_called_once_with()

def test_callback_status_deleted(simple_device):
    
    cb = Mock()

    status = simple_device._setup_move('inserted',
                                       finished_cb=cb)
    simple_device.component.put(0)
    status = simple_device._setup_move('removed')
    simple_device.component.put(1)
    assert status.done
    assert status.success
    cb.assert_called_once_with()

