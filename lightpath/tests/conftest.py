import logging
import os.path
from types import SimpleNamespace

import happi
import pytest
from ophyd import Component as Cpt
from ophyd import Device, Kind
from ophyd.signal import AttributeSignal
from ophyd.status import DeviceStatus
from ophyd.utils import DisconnectedError
from pcdsdevices.signal import AggregateSignal

from lightpath import BeamPath, LightpathState
from lightpath.controller import LightController


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
class SummarySignal(AggregateSignal):
    """
    Signal that holds a hash of the values of the constituent signals.

    Meant to allow tracking of constituent signals via callbacks.

    The calculated readback value is useless, and should not be used
    in any downstream calculations.  Use the signal/PV you actually
    care about instead.
    """
    def _calc_readback(self):
        values = tuple(sig.get() for sig in self._signals)
        # We return a hash here, rather than the tuple, to always provide
        # an ophyd-compatible datatype.
        return hash(values)


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
                        attr='status',
                        kind=Kind.hinted)
    current_transmission = Cpt(AttributeSignal,
                               attr='_transmission',
                               kind=Kind.normal)
    current_destination = Cpt(AttributeSignal,
                              attr='_current_destination',
                              kind=Kind.hinted)

    lightpath_summary = Cpt(SummarySignal, name='lp_summary',
                            kind='omitted')

    lightpath_cpts = ['current_state', 'current_transmission',
                      'current_destination']

    def __init__(self, prefix='', *, name, z, input_branches, output_branches):
        super().__init__(name, name=name)
        self.prefix = prefix
        self.md = SimpleNamespace()
        self.md.z = z
        self.input_branches = input_branches
        self.output_branches = output_branches
        self.status = Status.removed
        for sig in self.lightpath_cpts:
            self.lightpath_summary.add_signal_by_attr_name(sig)

    @property
    def _current_destination(self):
        """String returning current destination"""
        return self.output_branches[0]

    @property
    def _current_state(self):
        """String of state for current_state AttributeSignal"""
        return self.status

    def get_lightpath_state(self):
        """Return LightpathState object"""
        status = self.status
        if status == Status.disconnected:
            raise DisconnectedError("Simulated Disconnection")
        inserted = status in (Status.inserted, Status.inconsistent)
        removed = status in (Status.removed, Status.inconsistent)
        return LightpathState(
            inserted=inserted, removed=removed,
            transmission=self.current_transmission.get(),
            output_branch=self.current_destination.get()
        )

    def insert(self, timeout=None, finished_cb=None):
        """
        Insert the device into the beampath
        """
        # Complete request s.t. callbacks run
        self.current_state.put(Status.inserted)
        # Run subscriptions to device state
        self._run_subs(obj=self, sub_type=self._default_sub)
        # Return complete status object
        status = DeviceStatus(self)
        status.set_finished()
        return status

    def remove(self, wait=False, timeout=None, finished_cb=None):
        """
        Remove the device from the beampath
        """
        # Complete request
        self.current_state.put(Status.removed)
        # Run subscriptions to device state
        self._run_subs(obj=self, sub_type=self._default_sub)
        # Return complete status object
        status = DeviceStatus(self)
        status.set_finished()
        return status


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
    _transmission = 0.8

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _current_destination(self):
        """
        Return current beam destination
        """
        inserted = self.status in (Status.inserted, Status.inconsistent)
        removed = self.status in (Status.removed, Status.inconsistent)
        if inserted:
            return self.output_branches[1]

        elif removed:
            return self.output_branches[0]

        else:
            raise ValueError


############
# Fixtures #
############
# Basic Device
@pytest.fixture(scope='module')
def device():
    return Valve('valve', name='valve', z=40.0, input_branches=['TST'],
                 output_branches=['TST'])


# Basic Beamline
def simulated_path():
    # Assemble device lists
    devices = [Valve('zero', name='zero', z=0., input_branches=['TST'],
                     output_branches=['TST']),
               Valve('one', name='one', z=2., input_branches=['TST'],
                     output_branches=['TST']),
               Stopper('two', name='two', z=9., input_branches=['TST'],
                       output_branches=['TST']),
               Valve('three', name='three', z=15., input_branches=['TST'],
                     output_branches=['TST']),
               Crystal('four', name='four', z=16., input_branches=['TST'],
                       output_branches=['TST', 'SIM']),
               IPIMB('five', name='five', z=24., input_branches=['TST'],
                     output_branches=['TST']),
               Valve('six', name='six', z=30., input_branches=['TST'],
                     output_branches=['TST'])
               ]
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
    devices = [Valve('zero', name='zero', z=0., input_branches=['TST'],
                     output_branches=['TST']),
               Valve('one', name='one', z=2., input_branches=['TST'],
                     output_branches=['TST']),
               Stopper('two', name='two', z=9., input_branches=['TST'],
                       output_branches=['TST']),
               Valve('three', name='three', z=15., input_branches=['TST'],
                     output_branches=['TST']),
               Crystal('four', name='four', z=16., input_branches=['TST'],
                       output_branches=['TST', 'SIM']),
               IPIMB('five', name='five', z=24., input_branches=['SIM'],
                     output_branches=['SIM']),
               Valve('six', name='six', z=30., input_branches=['SIM'],
                     output_branches=['SIM'])]
    # Create semi-random order
    devices = sorted(devices, key=lambda d: d.prefix)
    # Create beampath
    return BeamPath(*devices, name='SIM')


# Simplified LCLS layout
@pytest.fixture(scope='function')
def lcls():
    return [Valve('FEE Valve 1', name='fee_val1', z=0., input_branches=['L0'],
                  output_branches=['L0']),
            Valve('FEE Valve 2', name='fee_val2', z=2., input_branches=['L0'],
                  output_branches=['L0']),
            Stopper('S2 Stopper', name='s2_st', z=9., input_branches=['L0'],
                    output_branches=['L0']),
            IPIMB('XRT IPM', name='xrt_ipm', z=15., input_branches=['L0'],
                  output_branches=['L0']),
            Crystal('XRT M1H', name='xrt_m1h', z=16., input_branches=['L0'],
                    output_branches=['L0', 'L3']),
            Valve('XRT Valve', name='xrt_valve', z=18., input_branches=['L0'],
                  output_branches=['L0']),
            Crystal('XRT M2H', name='xrt_m2h', z=20., input_branches=['L0'],
                    output_branches=['L0', 'L4']),
            IPIMB('HXR IPM', name='hxr_ipm', z=24., input_branches=['L0'],
                  output_branches=['L0']),
            Valve('HXR Valve', name='hxr_valve', z=25., input_branches=['L0'],
                  output_branches=['L0']),
            Stopper('S5 Stopper', name='s5_st', z=31., input_branches=['L0'],
                    output_branches=['L0']),
            Stopper('S4 Stopper', name='s4_st', z=32., input_branches=['L3'],
                    output_branches=['L3']),
            Stopper('S6 Stopper', name='s6_st', z=30., input_branches=['L4'],
                    output_branches=['L4']),
            IPIMB('MEC IPM', name='mec_ipm', z=24., input_branches=['L4'],
                  output_branches=['L4']),
            Valve('MEC Valve', name='mec_valve', z=25., input_branches=['L4'],
                  output_branches=['L4']),
            IPIMB('XCS IPM', name='xcs_ipm', z=21., input_branches=['L3'],
                  output_branches=['L3']),
            Valve('XCS Valve', name='xcs_valve', z=22., input_branches=['L3'],
                  output_branches=['L3'])]


@pytest.fixture(scope='function')
def lcls_client():
    db = os.path.join(os.path.dirname(__file__), 'path.json')
    print(db)
    return happi.Client(path=db)


@pytest.fixture(scope='function')
def lcls_ctrl(lcls_client: happi.Client):
    print(f'first item: {lcls_client.search()[0]}')
    return LightController(lcls_client)
