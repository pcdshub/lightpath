from types import SimpleNamespace

from ophyd import Component as Cpt
from ophyd import Device, Kind, Signal
from ophyd.status import DeviceStatus
from ophyd.utils import DisconnectedError
from pcdsdevices.signal import AggregateSignal

from .path import LightpathState


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
    _icon = 'fa5.adjust'

    current_state = Cpt(Signal, value=Status.removed,
                        kind=Kind.hinted)
    current_transmission = Cpt(Signal, value=0.0,
                               kind=Kind.normal)
    current_destination = Cpt(Signal, value='N/A',
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
        self.current_state.put(Status.removed)
        self.current_transmission.put(self._transmission)
        self.current_destination.put(self.output_branches[0])
        for sig in self.lightpath_cpts:
            self.lightpath_summary.add_signal_by_attr_name(sig)

    def get_lightpath_state(self):
        """Return LightpathState object"""
        status = self.current_state.get()
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
        # Return complete status object
        status = DeviceStatus(self)
        status.set_finished()
        return status


class IPIMB(Valve):
    """
    Generic Passive Device
    """
    _transmission = 0.5
    _icon = 'fa5s.th-large'


class Stopper(Valve):
    """
    Generic Veto Device
    """
    _veto = True
    _icon = 'fa5.times-circle'


class Crystal(Valve):
    """
    Generic branching device
    """
    _icon = 'fa5.star'
    _transmission = 0.8

    # when inserted, which branch do you take?
    _inserted_branch = Cpt(Signal, value=1)

    def get_lightpath_state(self):
        """
        Return current beam destination
        """
        state = super().get_lightpath_state()
        if state.inserted:
            br = self._inserted_branch.get()
            self.current_destination.put(self.output_branches[br])
            state.output_branch = self.output_branches[br]

        elif state.removed:
            self.current_destination.put(self.output_branches[0])
            state.output_branch = self.output_branches[0]

        return state
