#####
#####
import pytest
import logging
from   ophyd   import Signal
#####
#####
import lightpath
from lightpath import LightDevice
from lightpath.device import StateComponent

#lightpath.device.logger.addHandler(logging.StreamHandler())
lightpath.device.logger.setLevel(logging.DEBUG)

class FakeStateComponent(StateComponent):

    def __init__(self, value=None, transitions=None):
        super().__init__(None, read_only=False,
                        transitions=transitions)
        self.cls = Signal


    def create_component(self, instance):
        cpt_inst = super().create_component(instance)
        cpt_inst.put(1) #Do explicit put so that callback is run
                        #Just like a real PV will be
        return cpt_inst


class SimpleDevice(LightDevice):
    component = FakeStateComponent(transitions = {0 : 'inserted',
                                                  1 : 'removed',
                                                  2 : 'partially',
                                                  3 : 'bad_transition'}
                                  )

    def insert(self):
        self.component.put(0)

    def remove(self):
        self.component.put(1)

    def partial(self):
        self.component.put(2)


@pytest.fixture(scope='function')
def simple_device():
    device = SimpleDevice('DEVICE', name='simple', z = 10, beamline=40)
    return device

def test_initial_state(simple_device):
    assert simple_device.state == 'removed'

def test_insert(simple_device):
    simple_device.insert()
    assert simple_device.state == 'inserted'

def test_partial(simple_device):
    simple_device.partial()
    assert simple_device.state == 'partially'

def test_bad_transition(simple_device):
    simple_device.component.put(3)
    assert simple_device.state == 'unknown'
