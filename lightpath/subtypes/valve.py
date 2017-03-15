####################
# Standard Library #
####################
from enum import Enum

####################
#    Third Party   #
####################
from ophyd import Component, EpicsSignal, EpicsSignalRO
from ophyd.status import wait as status_wait

####################
#     Package      #
####################
from .utils import InterlockError
from  .. import LightDevice, StateComponent

class Commands(Enum):
    cls = 0
    opn = 1


class Valve(LightDevice):

    #EPICS Signals
    command   = Component(EpicsSignal,   ':OPN_SW')
    interlock = Component(EpicsSignalRO, ':OPN_OK')

    #EPICS State Signals
    open_limit   = StateComponent(':OPN_DI', read_only=True,
                                  transitions = {0 : 'defer', 1 : 'inserted'})
    closed_limit = StateComponent(':CLS_DI', read_only=True,
                                  transitions = {0 : 'defer', 1 : 'removed'})


    def insert(self, wait=False):
        """
        Close the gate valve
        """
        st = super().insert()
        self.command.put(Commands.cls.value)
        if wait:
            status_wait(st)
        return st


    @property
    def is_interlocked(self):
        """
        Whether interlock is active, preventing valve from opening
        """
        return bool(self.interlock.get())


    def remove(self, wait=False): 
        """
        Open the gate valve
        """
        if self.is_interlocked:
            raise InterlockError('Valve is currently forced closed '
                                 'by vacuum logic.')

        st = super().remove()
        self.command.put(Commands.opn.value)
        if wait:
            status_wait(st)
        return st
