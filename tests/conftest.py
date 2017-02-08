import pytest
import logging
import numpy as np
from ophyd import Signal
from ophyd.device import Component

import lightpath
from lightpath import BeamPath, LightDevice
from lightpath.device import StateComponent

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
    _beamline     = 'LCLS'
    _transmission = 0.


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    basic = Component(Signal, value=4,)

    _transmission = .5
    _beamline = 'LCLS'

    def __init__(self, *args, **kwargs):
        kwargs['configuration_attrs'] = ['basic']
        super().__init__(*args, **kwargs)

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

class SimpleMirror(SimpleDevice):

    _destination  = 'HXR'
    _branching    = ['SXR', 'HXR']
    _transmission = 1.

    def __init__(self , *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.insert()

    @property
    def destination(self):
        if self.inserted:
            return self._destination
        
        else:
            return None



@pytest.fixture(scope='function')
def simple_device():
    device = SimpleDevice('SIMPLE', name='simple', z = 4)
    return device

@pytest.fixture(scope='function')
def simple_mirror():
    device = SimpleMirror('MIRROR', name='mirror', z = 15.5)
    return device

@pytest.fixture(scope='function')
def complex_device():
    device = ComplexDevice('COMPLEX', name='complex', z = 10)
    return device


@pytest.fixture(scope='function')
def beampath(simple_device, complex_device, simple_mirror):
    devices = [SimpleDevice('DEVICE_1', name='one',   z = 0.),
               SimpleDevice('DEVICE_2', name='two',   z = 2.),
               SimpleDevice('DEVICE_3', name='three', z = 9.),
               SimpleDevice('DEVICE_4', name='four',  z = 15.),
               SimpleDevice('DEVICE_5', name='five',  z = 16., beamline='HXR'),
               SimpleDevice('DEVICE_6', name='six',   z = 30., beamline='HXR'),
               simple_mirror,
               simple_device,
               complex_device,
              ]
    bp = BeamPath(*devices)
    return bp
