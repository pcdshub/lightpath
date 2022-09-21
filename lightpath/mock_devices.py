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

    def subscribe(self, *args, **kwargs):
        cid = super().subscribe(*args, **kwargs)

        # For some reason meta callbacks need to be run again
        for sig in self._signals:
            sig._run_metadata_callbacks()

        return cid


class Status:
    """
    Hold pseudo-status
    """
    inserted = 0
    removed = 1
    unknown = 2
    inconsistent = 3
    disconnected = 4


class BaseValve(Device):
    """
    Basic device to facilitate in/out positioning
    """
    _transmission = 0.0
    _veto = False
    SUB_STATE = 'sub_state_changed'
    _default_sub = SUB_STATE
    _icon = 'fa5s.adjust'

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
        if removed and not inserted:
            trans = 1
        else:
            trans = self.current_transmission.get()
        return LightpathState(
            inserted=inserted, removed=removed,
            output={self.current_destination.get(): trans}
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


class Valve(BaseValve):
    """ subclass to differentiate from other mock devices """
    pass


class IPIMB(BaseValve):
    """
    Generic Passive Device
    """
    _transmission = 0.5
    _icon = 'fa5s.th-large'


class Stopper(BaseValve):
    """
    Generic Veto Device
    """
    _veto = True
    _icon = 'fa5.times-circle'

    def get_lightpath_state(self):
        state = super().get_lightpath_state()

        # removed, set transmission -> 1
        if not state.inserted and state.removed:
            # should only have one key
            br = list(state.output.keys())[0]
            state.output[br] = 1
            return state
        return state


class Crystal(BaseValve):
    """
    Generic branching device, allowing more than 2 output branches
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
            state.output = {self.output_branches[br]: 0.8}

        elif state.removed:
            self.current_destination.put(self.output_branches[0])
            state.output = {self.output_branches[0]: 1}

        return state


class LODCM(BaseValve):
    """
    LODCM device that can allow beam to two destinations at once.
    States are:

    - OUT (0): beam passes through, LODCM is removed
    - IN-1 (1): beam splits between two output branches
    - IN-2 (2): beam diverted to second output branch
    """

    # when inserted, which insertion mode??
    _inserted_mode = Cpt(Signal, value=1)

    def get_lightpath_state(self):
        state = super().get_lightpath_state()
        if state.inserted:
            mode = self._inserted_mode.get()
            # self.current_destination.put(self.output_branches[br])
            if mode == 1:
                state.output = {self.output_branches[0]: 0.5,
                                self.output_branches[1]: 0.5}
            elif mode == 2:
                state.output = {self.output_branches[0]: 0,
                                self.output_branches[1]: 0.5}

        elif state.removed:
            # self.current_destination.put(self.output_branches[0])
            state.output = {self.output_branches[0]: 1}

        return state
