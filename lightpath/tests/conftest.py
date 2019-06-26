import os.path
import logging
from types import SimpleNamespace

import happi
import pytest
from ophyd import Device, Kind, Component as Cpt
from ophyd.signal import AttributeSignal
from ophyd.status import DeviceStatus
from ophyd.utils import DisconnectedError

import lightpath
from lightpath import BeamPath


#################
# Logging Setup #
#################
# Enable the logging level to be set from the command line
def pytest_addoption(parser):
    parser.addoption("--log", action="store", default="DEBUG",
                     help="Set the level of the log")
    parser.addoption("--logfile", action="store", default='log',
                     help="Write the log output to specified file path")


# Create a fixture to automatically instantiate logging setup
@pytest.fixture(scope='session', autouse=True)
def set_level(pytestconfig):
    # Read user input logging level
    log_level = getattr(logging, pytestconfig.getoption('--log'), None)

    # Report invalid logging level
    if not isinstance(log_level, int):
        raise ValueError("Invalid log level : {}".format(log_level))

    # Create basic configuration
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
    removed = 1
    unknown = 2
    inconsistent = 3
    disconnected = 4


class Valve(Device):
    """
    Basic device to facilitate in/out positioning
    """
    _transmission = 0.0
    _veto = False
    SUB_STATE = 'sub_state_changed'
    _default_sub = SUB_STATE
    _icon = 'fa.adjust'

    current_state = Cpt(AttributeSignal,
                        attr='_current_state',
                        kind=Kind.hinted)
    current_transmission = Cpt(AttributeSignal,
                               attr='transmission',
                               kind=Kind.normal)

    def __init__(self, name, z, beamline):
        super().__init__(name, name=name)
        self.md = SimpleNamespace()
        self.md.z = z
        self.md.beamline = beamline
        self.status = Status.removed

    @property
    def _current_state(self):
        """String of state for current_state AttributeSignal"""
        return self.status

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
        if self.status == Status.disconnected:
            raise DisconnectedError("Simulated Disconnection")
        return self.status in (Status.inserted, Status.inconsistent)

    @property
    def removed(self):
        """
        Report if the device is inserted into the beam
        """
        return self.status in (Status.removed, Status.inconsistent)

    def insert(self, timeout=None, finished_cb=None):
        """
        Insert the device into the beampath
        """
        # Complete request
        self.status = Status.inserted
        # Run subscriptions to device state
        self._run_subs(obj=self, sub_type=self._default_sub)
        # Return complete status object
        return DeviceStatus(self, done=True, success=True)

    def remove(self, wait=False, timeout=None, finished_cb=None):
        """
        Remove the device from the beampath
        """
        # Complete request
        self.status = Status.removed
        # Run subscriptions to device state
        self._run_subs(obj=self, sub_type=self._default_sub)
        # Return complete status object
        return DeviceStatus(self, done=True, success=True)


class IPIMB(Valve):
    """
    Generic Passive Device
    """
    _transmission = 0.6
    _icon = 'fa.th-large'


class Stopper(Valve):
    """
    Generic Veto Device
    """
    _veto = True
    _icon = 'fa.times-circle'


class Crystal(Valve):
    """
    Generic branching device
    """
    _icon = 'fa.star'

    def __init__(self, name, z, beamline, states):
        super().__init__(name, z, beamline)
        self.states = states
        self.branches = [dest for state in self.states
                         for dest in state]

    @property
    def destination(self):
        """
        Return current beam destination
        """
        if self.inserted:
            return self.states[1]

        elif self.removed:
            return self.states[0]

        else:
            return self.branches


############
# Fixtures #
############
# Basic Device
@pytest.fixture(scope='module')
def device():
    return Valve('valve', z=40.0, beamline='TST')


# Basic Beamline
def simulated_path():
    # Assemble device lists
    devices = [Valve('zero', z=0., beamline='TST'),
               Valve('one', z=2., beamline='TST'),
               Stopper('two', z=9., beamline='TST'),
               Valve('three', z=15., beamline='TST'),
               Crystal('four', z=16.,
                       beamline='TST', states=[['TST'], ['SIM']]),
               IPIMB('five', z=24., beamline='TST'),
               Valve('six', z=30., beamline='TST')]
    # Create semi-random order
    devices = sorted(devices, key=lambda d: d.prefix)
    # Create beampath
    return BeamPath(*devices, name='TST')


@pytest.fixture(scope='function')
def path():
    return simulated_path()


# Beamline that requires optic insertion
@pytest.fixture(scope='function')
def branch():
    # Assemble device lists
    devices = [Valve('zero', z=0., beamline='TST'),
               Valve('one', z=2., beamline='TST'),
               Stopper('two', z=9., beamline='TST'),
               Valve('three', z=15., beamline='TST'),
               Crystal('four', z=16., beamline='TST',
                       states=[['TST'], ['SIM']]),
               IPIMB('five', z=24., beamline='SIM'),
               Valve('six', z=30., beamline='SIM')]
    # Create semi-random order
    devices = sorted(devices, key=lambda d: d.prefix)
    # Create beampath
    return BeamPath(*devices, name='SIM')


# Simplified LCLS layout
@pytest.fixture(scope='function')
def lcls():
    return [Valve('FEE Valve 1', z=0., beamline='HXR'),
            Valve('FEE Valve 2', z=2., beamline='HXR'),
            Stopper('S2 Stopper', z=9., beamline='HXR'),
            IPIMB('XRT IPM', z=15., beamline='HXR'),
            Crystal('XRT M1H', z=16., beamline='HXR',
                    states=[['MEC', 'CXI'], ['XCS']]),
            Valve('XRT Valve', z=18., beamline='HXR'),
            Crystal('XRT M2H', z=20., beamline='HXR',
                    states=[['CXI', 'XCS'], ['MEC']]),
            IPIMB('HXR IPM', z=24., beamline='CXI'),
            Valve('HXR Valve', z=25., beamline='CXI'),
            Stopper('S5 Stopper', z=31., beamline='CXI'),
            Stopper('S4 Stopper', z=32., beamline='XCS'),
            Stopper('S6 Stopper',  z=30., beamline='MEC'),
            IPIMB('MEC IPM', z=24., beamline='MEC'),
            Valve('MEC Valve', z=25., beamline='MEC'),
            IPIMB('XCS IPM', z=21., beamline='XCS'),
            Valve('XCS Valve', z=22., beamline='XCS')]


@pytest.fixture(scope='function')
def lcls_client():
    # Reset the configuration database
    lightpath.controller.beamlines = {'MEC': {'HXR': {}},
                                      'CXI': {'HXR': {}},
                                      'XCS': {'HXR': {}}}
    db = os.path.join(os.path.dirname(__file__), 'path.json')

    return happi.Client(path=db)
