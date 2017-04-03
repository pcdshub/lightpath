import pytest
import logging
import numpy as np
from ophyd import Signal
from ophyd.device import Component

import lightpath
from lightpath import MPS, BeamPath, LightDevice
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

class SimpleMPS(MPS):

    bypass = Component(Signal, value=0)
    alarm  = Component(Signal, value=0)

class MPSDevice(SimpleDevice):

    switches = Component(SimpleMPS,'basic', veto=False)

    def insert(self, timeout=None):
        self.mps.alarm.put(2)
        return super().insert(timeout=None)

    def remove(self, timeout=None):
        self.mps.alarm.put(0)
        return super().remove(timeout=None)

class VetoDevice(SimpleDevice):

    switches = Component(SimpleMPS,'basic', veto=True)


@pytest.fixture(scope='function')
def simple_device():
    device = SimpleDevice('SIMPLE', alias='simple', z = 4)
    return device

@pytest.fixture(scope='function')
def simple_mirror():
    device = SimpleMirror('MIRROR', alias='mirror', z = 15.5)
    return device

@pytest.fixture(scope='function')
def complex_device():
    device = ComplexDevice('COMPLEX', alias='complex', z = 10)
    return device


@pytest.fixture(scope='function')
def beampath(simple_device, complex_device, simple_mirror):
    devices = [SimpleDevice('DEVICE_1', alias='one',   z = 0.),
               SimpleDevice('DEVICE_2', alias='two',   z = 2.),
               SimpleDevice('DEVICE_3', alias='three', z = 9.),
               SimpleDevice('DEVICE_4', alias='four',  z = 15.),
               SimpleDevice('DEVICE_5', alias='five',  z = 16., beamline='HXR'),
               SimpleDevice('DEVICE_6', alias='six',   z = 30., beamline='HXR'),
               simple_mirror,
               simple_device,
               complex_device,
              ]
    bp = BeamPath(*devices, name='TST')
    return bp

@pytest.fixture(scope='function')
def mps():
    return SimpleMPS('basic', veto=False)

@pytest.fixture(scope='function')
def mps_device():
    mps= MPSDevice('basic', z=8.3,  beamline='LCLS')
    return mps

@pytest.fixture(scope='function')
def mps_path():
    first_veto  = VetoDevice('veto_1', z=8.3,  beamline='LCLS')
    second_veto = VetoDevice('veto_2', z=14.3, beamline='LCLS')
    first_mps   = MPSDevice('mps_1',   z=8.8, beamline='LCLS')
    second_mps  = MPSDevice('mps_2',   z=18.8, beamline='LCLS')

    return BeamPath(first_veto, second_veto,
                    second_mps, first_mps,
                    name='TST')
