import contextlib
import dataclasses
from collections.abc import Generator
from threading import RLock
from types import SimpleNamespace
from typing import Optional, Union

import numpy.typing as npt
import ophyd
from ophyd import Component as Cpt
from ophyd import Device, Kind, Signal
from ophyd.status import DeviceStatus
from ophyd.utils import DisconnectedError

from .path import LightpathState

#####################
# Simulated Classes #
#####################
OphydBaseType = Union[
    str,
    int,
    bool,
    float,
]
OphydDataType = Union[
    OphydBaseType,
    list[OphydBaseType],
    npt.NDArray[OphydBaseType]
]


@dataclasses.dataclass
class _AggregateSignalState:
    """
    This class holds per-Signal state information when used as part of an
    AggregateSignal.

    It includes a cache of the last value, connectivity status, and callback
    identifiers from ophyd.
    """
    #: The signal itself
    signal: Signal
    #: Is the signal connected according to its metadata callback?
    connected: bool = False
    #: The last value retrieved from a value callback, or a direct get request.
    value: Optional[OphydDataType] = None
    #: The value subscription callback ID (None if not yet subscribed)
    value_cbid: Optional[int] = None
    #: The meta subscription callback ID (None if not yet subscribed)
    meta_cbid: Optional[int] = None


class AggregateSignal(Signal):
    """
    Signal that is composed of a number of other signals.

    This class exists to handle the group subscriptions without repeatedly
    getting the values of all the subsignals at all times.

    This signal type is intended to be used programmatically with a subclass.
    For simple per-device usage, see :class:`MultiDerivedSignal`.
    """

    _update_only_on_change: bool = True
    _has_subscribed: bool
    _signals: dict[Signal, _AggregateSignalState]

    def __init__(self, *, name, value=None, **kwargs):
        super().__init__(name=name, value=value, **kwargs)
        self._has_subscribed = False
        self._lock = RLock()
        self._signals = {}

    def _calc_readback(self):
        """
        Override this with a calculation to find the current state given the
        cached values.

        Returns
        -------
        readback
            The result of the calculation.
        """

        raise NotImplementedError(
            'Subclasses must implement _calc_readback'
        )  # pragma nocover

    def _insert_value(self, signal, value):
        """Update the cache with one value and recalculate."""
        with self._lock:
            self._signals[signal].value = value
            self._update_readback()
            return self._readback

    @property
    def _have_values(self) -> bool:
        """Is the value cache populated?"""
        return all(
            siginfo.value is not None for siginfo in self._signals.values()
        )

    def _update_readback(self) -> Optional[OphydDataType]:
        """
        Recalculate the readback value.

        Requires that the signal info cache has been updated prior to the
        call.  This information could be sourced via subscriptions or manually
        queried updates as in ``.get()``.

        Returns
        -------
        value : OphydDataType or None
            This is the newly-calculated value, if available. If there are
            missing values in the cache, the previously-calculated readback
            value (or the default passed into the ``Signal`` instance or
            ``None``) will be returned.
        """
        with self._lock:
            if self._have_values:
                self._readback = self._calc_readback()
            return self._readback

    def get(self, **kwargs):
        """
        Update all values and recalculate.

        Parameters
        ----------
        **kwargs :
            Keyword arguments are passed to each ``signal.get(**kwargs)``.
        """
        with self._lock:
            for signal, siginfo in self._signals.items():
                siginfo.value = signal.get(**kwargs)
            return self._update_readback()

    def put(self, value, **kwargs):
        raise NotImplementedError(
            'put should be overridden in a subclass'
        )  # pragma nocover

    def subscribe(self, cb, event_type=None, run=True):
        cid = super().subscribe(cb, event_type=event_type, run=run)
        recognized_event = event_type in (None, self.SUB_VALUE, self.SUB_META)
        if recognized_event and not self._has_subscribed:
            self._setup_subscriptions()

        return cid

    subscribe.__doc__ = ophyd.ophydobj.OphydObject.subscribe.__doc__

    def _setup_subscriptions(self):
        """Subscribe to all relevant signals."""
        with self._lock:
            if self._has_subscribed:
                return

            self._has_subscribed = True

        try:
            for signal, siginfo in self._signals.items():
                self.log.debug("Subscribing %s", signal.name)
                if siginfo.value_cbid is not None:
                    # Only subscribe once.
                    continue

                siginfo.meta_cbid = signal.subscribe(
                    self._signal_meta_callback,
                    run=True,
                    event_type=signal.SUB_META,
                )
                siginfo.value_cbid = signal.subscribe(
                    self._signal_value_callback,
                    run=True,
                )
        except Exception:
            self.log.exception("Failed to subscribe to signals")

    def wait_for_connection(self, *args, **kwargs):
        """Wait for underlying signals to connect."""
        self._setup_subscriptions()
        return super().wait_for_connection(*args, **kwargs)

    def _signal_meta_callback(
        self, *, connected: bool = False, obj: Signal, **kwargs
    ) -> None:
        """This is a SUB_META callback from one of the aggregated signals."""
        with self._check_connectivity():
            self._signals[obj].connected = connected

    def _signal_value_callback(self, *, obj: Signal, **kwargs):
        """This is a SUB_VALUE callback from one of the aggregated signals."""
        kwargs.pop('sub_type')
        kwargs.pop('old_value')
        value = kwargs['value']
        with self._lock:
            old_value = self._readback
            # Update just one value and assume the rest are cached
            # This allows us to run subs without EPICS gets
            # Run metadata callbacks before the value callback, if appropriate
            with self._check_connectivity() as connectivity_info:
                value = self._insert_value(obj, value)
            if connectivity_info["sent_value_callback"]:
                # Avoid sending a duplicate SUB_VALUE event since the
                # connectivity check above did it already
                return
            if value != old_value or not self._update_only_on_change:
                self._run_subs(sub_type=self.SUB_VALUE, obj=self, value=value,
                               old_value=old_value)

    @property
    def connected(self) -> bool:
        """Are all relevant signals connected?"""
        if self._destroyed:
            return False

        if self._has_subscribed:
            return all(
                siginfo.connected and siginfo.value is not None
                for siginfo in self._signals.values()
            )

        # Only check connectivity status of the signal; cross fingers that it
        # reflects both being connected and having a not-None value.
        return all(signal.connected for signal in self._signals)

    @contextlib.contextmanager
    def _check_connectivity(self) -> Generator[dict[str, bool], None, None]:
        """
        Context manager for checking connectivity.

        The block for the context manager should perform some operation
        to change the state of the signal.

        Returns state information as a dictionary, accessible after the
        context manager block has finished evaluation.
        """
        was_connected = self.connected
        state_info = {
            "was_connected": was_connected,
            "is_connected": was_connected,
            "sent_md_callback": False,
            "sent_value_callback": False,
        }

        yield state_info

        # Now that the caller has updated state, check to see if our
        # connectivity status has changed.  Update the mutable return
        # value at this point.
        is_connected = self.connected
        state_info["is_connected"] = is_connected
        if was_connected != is_connected:
            self._metadata["connected"] = is_connected
            self._run_metadata_callbacks()
            state_info["sent_md_callback"] = True

        if not was_connected and is_connected:
            # disconnected -> connected; give a proper value callback.
            # "connected" indicates that:
            # 1. All underlying signals are connected
            # 2. All underlying signals have a value cached
            with self._lock:
                old_value = self._readback
                self._readback = self._calc_readback()
                self._run_subs(
                    sub_type=self.SUB_VALUE,
                    obj=self,
                    value=self._readback,
                    old_value=old_value,
                )
                state_info["sent_value_callback"] = True

    def add_signal_by_attr_name(self, name: str) -> Signal:
        """
        Add a signal from which to aggregate information.

        This must be called before any subscriptions are made to the signal.
        Duplicate signals will not be re-added.

        Parameters
        ----------
        name : str
            The attribute name of the signal, relative to the parent device.

        Returns
        -------
        sig : ophyd.Signal
            The signal referenced by the attribute name.

        Raises
        ------
        RuntimError
            If called after .subscribe() or used without a parent Device.
        """
        if self._has_subscribed:
            raise RuntimeError(
                "Cannot add signals to an AggregateSignal after it has been "
                "subscribed to."
            )

        sig = self.parent

        if sig is None:
            raise RuntimeError(
                "Cannot use an AggregateSignal with attribute names outside "
                "of a Device/Component hierarchy."
            )

        for part in name.split('.'):
            sig = getattr(sig, part)

        # Add if not yet there; but do not subscribe just yet.
        self._signals[sig] = _AggregateSignalState(signal=sig)
        return sig

    def destroy(self):
        for signal, info in self._signals.items():
            if info.value_cbid is not None:
                signal.unsubscribe(info.value_cbid)
                info.value_cbid = None

            if info.meta_cbid is not None:
                signal.unsubscribe(info.meta_cbid)
                info.meta_cbid = None

        return super().destroy()


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
