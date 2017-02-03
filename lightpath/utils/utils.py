from enum import Enum
from super_state_machine.machines import StateMachine
from super_state_machine.extras   import PropertyMachine
from super_state_machine.errors   import TransitionError

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

    @classmethod
    def states(cls):
        return [state.value for state in cls]

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

