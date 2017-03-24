####################
# Standard Library #
####################
from enum import Enum

####################
#    Third Party   #
####################
from ophyd import Device, EpicsSignalRO, Component
from ophyd.utils.epics_pvs import raise_if_disconnected, AlarmSeverity
from super_state_machine.machines import StateMachine
from super_state_machine.extras   import PropertyMachine
from super_state_machine.errors   import TransitionError

####################
#     Package      #
####################

class MPS(Device):
    """
    Parameters
    ----------
    prefix : str
        Base PV address for all related records

    veto : bool, optional
        Whether the device is considered a veto device in MPS
    """
    bypass = Component(EpicsSignalRO, '_BYPS')
    alarm  = Component(EpicsSignalRO, '_MPSC.SEVR')

    SUB_MPS = 'mps_state_switched'
    _default_sub  = SUB_MPS

    def __init__(self, *args, veto=False, **kwargs):

        self._veto = veto

        super().__init__(*args, **kwargs)
        
        #Subscribe to changes of state 
        self.alarm.subscribe(self._mps_change)
        self.bypass.subscribe(self._mps_change)


    @property
    @raise_if_disconnected
    def bypassed(self):
        """
        Whether component is currently bypassed
        """
        return bool(self.bypass.get())


    @property
    @raise_if_disconnected
    def faulted(self):
        """
        Whether device is currently in a faulted state or not
        """
        if self.bypassed:
            return False

        else:
            return self.alarm.get() == AlarmSeverity.MAJOR.value


    @property
    def veto_capable(self):
        """
        Whether the MPS will ignore upstream faults with this device inserted
        """
        return self._veto


    def _mps_change(self, *args, **kwargs):
        """
        Callback for change in MPS status
        """
        self._run_subs(sub_type = self.SUB_MPS,
                       faulted = self.faulted) 

class DeviceStateMachine(StateMachine):
    """
    State Machine for device transitions
    """
    class States(Enum):
        """
        Four way state
        """
        INSERTED   = 'inserted'
        REMOVED    = 'removed'
        UNKNOWN    = 'unknown'


    class Meta:
        allow_empty   = False
        initial_state = 'unknown'


class LoggingPropertyMachine(PropertyMachine):
    """
    Creates a property in the parent device that uses the built in logger
    """
    def __init__(self, machine_type):
        super().__init__(machine_type)

    def __set__(self, obj, value):
        old_value = self.__get__(obj)
        super().__set__(obj, value)
        value = self.__get__(obj)
        obj.log.info('Change state on %r from %r -> %r',
                     obj, old_value, value)

