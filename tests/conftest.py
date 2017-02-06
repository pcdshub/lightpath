import pytest
import logging
from ophyd   import Signal

import lightpath
from   lightpath import BeamPath, LightDevice
from   lightpath.device import StateComponent

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
                                                  2 : 'bad_transition'}
                                  )

    def insert(self,timeout=None):
        status = super().insert(timeout=timeout)
        self.component.put(0)
        return status

    def remove(self,timeout=None):
        status = super().remove(timeout=timeout)
        self.component.put(1)
        return status


class ComplexDevice(LightDevice):
    opn = FakeStateComponent(transitions = {0 : 'defer',
                                            1 : 'removed',
                            })
    cls = FakeStateComponent(transitions = {0 : 'inserted',
                                            1 : 'defer',
                            })

    def insert(self, timeout=None):
        status = super().insert(timeout=timeout)
        self.opn.put(0)
        self.cls.put(0)
        return status 

    def remove(self, timeout=None):
        status = super().remove(timeout=timeout)
        self.opn.put(1)
        self.cls.put(1)
        return status

@pytest.fixture(scope='function')
def simple_device():
    device = SimpleDevice('DEVICE', name='simple', z = 10, beamline=40)
    return device

@pytest.fixture(scope='function')
def complex_device():
    device = ComplexDevice('DEVICE', name='simple', z = 10, beamline=40)
    return device


@pytest.fixture(scope='module')
def beampath():
    devices = [SimpleDevice('DEVICE_1', name='first',  z = 0.),
               SimpleDevice('DEVICE_2', name='second', z = 2.),
               SimpleDevice('DEVICE_3', name='third',  z = 9.),
               SimpleDevice('DEVICE_4', name='fourth', z = 15.),
               SimpleDevice('DEVICE_5', name='fifth',  z = 16.),
               SimpleDevice('DEVICE_6', name='sixth',  z = 30.),
              ]
    return BeamPath(*devices)
