############
# Standard #
############
import logging
from enum import Enum

###############
# Third Party #
###############
import pytest
import numpy as np
from ophyd.device import Device
from ophyd.status import DeviceStatus

##########
# Module #
##########
from lightpath import LightInterface, BeamPath

#################
# Logging Setup #
#################
#Enable the logging level to be set from the command line
def pytest_addoption(parser):
    parser.addoption("--log", action="store", default="INFO",
                     help="Set the level of the log")
    parser.addoption("--logfile", action="store", default=None,
                     help="Write the log output to specified file path")

#Create a fixture to automatically instantiate logging setup
@pytest.fixture(scope='session', autouse=True)
def set_level(pytestconfig):
    #Read user input logging level
    log_level = getattr(logging, pytestconfig.getoption('--log'), None)

    #Report invalid logging level
    if not isinstance(log_level, int):
        raise ValueError("Invalid log level : {}".format(log_level))

    #Create basic configuration
    logging.basicConfig(level=log_level,
                        filename=pytestconfig.getoption('--logfile'))

#####################
# Simulated Classes #
#####################
class Status:
    """
    Hold pseudo-status
    """
    inserted = 0
    removed  = 1
    unknown  = 2


class Valve(Device, metaclass=LightInterface):
    """
    Basic device to facilitate in/out positioning
    """
    _transmission = 0.0
    _veto         = False
    SUB_DEV_CH    = 'device_state_changed'
    _default_sub  = SUB_DEV_CH

    def __init__(self, name, z, beamline):
        super().__init__(name)
        self.z    = z
        self.beamline     = beamline
        self.status = Status.removed
        self.mps    = MPS(self)


    @property
    def transmission(self):
        """
        Transmission of device
        """
        return self._transmission


    @property
    def inserted(self):
        """
        Report if the device is inserted into the beam
        """
        return self.status == Status.inserted


    @property
    def removed(self):
        """
        Report if the device is inserted into the beam
        """
        return self.status == Status.removed


    def insert(self, timeout=None, finished_cb=None):
        """
        Insert the device into the beampath
        """
        self.status = Status.inserted
        self._run_subs(obj=self, sub_type=self._default_sub)
        return DeviceStatus(self, done=True, success=True)


    def remove(self, timeout=None, finished_cb=None):
        """
        Remove the device from the beampath
        """
        self.status = Status.removed
        self._run_subs(obj=self, sub_type=self._default_sub)
        return DeviceStatus(self, done=True, success=True)


class IPIMB(Valve):
    """
    Generic Passive Device
    """
    _transmission = 0.6


class Stopper(Valve):
    """
    Generic Veto Device
    """
    _veto = True


class Crystal(Valve):
    """
    Generic branching device
    """
    def __init__(self, name, z, beamline, branch):
        super().__init__(name, z, beamline)
        self.branches = [self.beamline, branch]
        self.mps      = None

    @property
    def destination(self):
        """
        Return current beam destination
        """
        if self.inserted:
            return [self.branches[1]]

        elif self.removed:
            return [self.beamline]

        else:
            return self.branches


class MPS(object):
    """
    Simulated MPS device
    """
    def __init__(self, device):
        self.device   = device
        self.bypassed = False

    @property
    def faulted(self):
        """
        MPS is faulted if device is inserted and not bypassed
        """
        return (self.device.inserted 
                and not self.bypassed
                and not self.veto_capable)

    @property
    def veto_capable(self):
        """
        Veto device
        """
        return self.device._veto

############
# Fixtures #
############

#Basic Beamline
@pytest.fixture(scope='function')
def path():
    #Assemble device lists
    devices = [Valve('zero',     z=0.,  beamline='TST'),
               Valve('one',      z=2.,  beamline='TST'),
               Stopper('two',    z=9.,  beamline='TST'),
               Valve('three',    z=15., beamline='TST'),
               Crystal('four',   z=16., beamline='TST', branch='SIM'),
               IPIMB('five',     z=24., beamline='TST'),
               Valve('six',      z=30., beamline='TST'),
              ]
    #Create semi-random order
    devices = sorted(devices, key=lambda d : d.prefix)
    #Create beampath
    return BeamPath(*devices, name='TST')

#Beamline that requires optic insertion
@pytest.fixture(scope='function')
def branch():
    #Assemble device lists
    devices = [Valve('zero',     z=0.,  beamline='TST'),
               Valve('one',      z=2.,  beamline='TST'),
               Stopper('two',    z=9.,  beamline='TST'),
               Valve('three',    z=15., beamline='TST'),
               Crystal('four',   z=16., beamline='TST', branch='SIM'),
               IPIMB('five',     z=24., beamline='SIM'),
               Valve('six',      z=30., beamline='SIM'),
              ]
    #Create semi-random order
    devices = sorted(devices, key=lambda d : d.prefix)
    #Create beampath
    return BeamPath(*devices, name='SIM')
