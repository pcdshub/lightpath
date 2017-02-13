####################
# Standard Library #
####################

####################
#    Third Party   #
####################
from ophyd import Device, EpicsSignalRO, Component
from ophyd.utils.epics_pvs import raise_if_disconnected, AlarmSeverity

####################
#     Package      #
####################


class MPS(Device):
    """
    Parameters
    ----------
    prefix : str
        Base PV address for all related records
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

