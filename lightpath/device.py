import logging
from threading import RLock

import numpy as np
from functools import partial

from ophyd        import Device
from ophyd.device import Component
from ophyd.signal import EpicsSignal, EpicsSignalRO
from ophyd.status import DeviceStatus

from .utils import DeviceStateMachine, LoggingPropertyMachine

logger = logging.getLogger(__name__)


class StateComponent(Component):

    SUB_CP_CH= 'component_state_changed'

    def __init__(self, suffix, read_only=True, transitions=None):
            #Transitions are mandatory
            if not transitions:
                raise ValueError('State Component must have associated '
                                 'transitions dictionary')

            #Setup state variables
            self.state       = 'unknown'
            self.transitions = dict(transitions)

            #Pick correct class
            if read_only:
                cls = EpicSignalRO

            else:
                cls = EpicsSignal

            super().__init__(cls, suffix=suffix)


    def create_component(self, instance):
        """
        Add transitions dictionary to created component
        """
        cpt_inst = super().create_component(instance)
        cpt_inst.subscribe(self.update, run=True)
        return cpt_inst

    def update(self, *args, old_value=None, value=None, obj=None, **kwargs):
        """
        Callback to change state of Component
        """
        logger.debug('Update caused by {} from {} -> {}'.format(obj.name,
                                                                old_value,
                                                                value))
        #Check that we are in fact getting a new valu 
        if old_value ==value:
            logger.debug('No state change ...')
            return 

        try:
            #Keep track of transition
            transition = self.transitions[value]

            #Check that transition is valid
            if transition not in ('inserted','removed',
                                  'unknown', 'defer'):
                logger.critical('Unsupported transition {} by {}'
                                 ''.format(transition, obj.name))
                #Make unknown if invalid
                transition  = 'unknown'

        #By default if a component is an unknown state
        #The device is unknown
        except KeyError:
            transition = 'unknown'
            logger.warning('Device {} received an unknown value from '
                           'signal {}'.format(self.name, obj.name))


        finally:
            self.state, old_value =  transition, self.state

            logger.debug('Signal {} transitioned from {} -> {} ...'
                         ''.format(obj.name, old_value, self.state))

            #Run subscriptions in parent
            if obj.parent and self.SUB_CP_CH in obj.parent._subs:
                obj.parent._run_subs(sub_type = self.SUB_CP_CH,
                                     old_value=old_value,
                                     value = self.state)


class LightInterface:
    """
    Generic Interface for LightDevice

    Subclasses can safely reimplement these methods without breaking mro
    """
    _beamline     = None
    _z            = -1.0
    _transmission = 0.
    _branching    = []
    _passive      = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    @property
    def z(self):
        """
        Z position along the beamline 
        """
        return self._z


    @property
    def beamline(self):
        """
        Specific beamline the device is on
        """
        return self._beamline

    @property
    def destination(self):
        """
        Name of the destination beamline after the beam interacts with the
        device.
        """
        return self._beamline


    @property
    def transmission(self):
        """
        Current transmission through the device
        """
        if self.passive:
            return 1.

        else:
            return self._transmission


    @property
    def branching(self):
        """
        Other possible beamlines the device is capable of sending the
        beam
        """
        return self._branching


    @property
    def passive(self):
        """
        Whether the device is considered passive or not
        """
        return self._passive


    def home(self):
        """
        Home the device
        """
        pass


    def verify(self):
        """
        Verify that the beam is actually incident upon the device
        """
        pass


class LightDevice(Device, LightInterface):
    """
    Base class to represent a device along the Lightpath

    The main function of this class is to define a standard API for further
    device classes to reuse based on their individual states. Each class that
    inherits this as its base should reimplement the following methods;
    :meth:`.insert`, :meth:`.remove`, :attr:`.destination` and :meth:`.home`.
    Also, if the device has a more complex relationship with the beam than
    blocking or not, it may be neccesary to reimplement :attr:`.transmission`.
    Finally, if the device is capable of measuring the presence of beam,
    rewriting the :meth:`.verify` can be overwritten as well to be used by the
    LightPath client to check the predicted beamline state

    Parameters
    ----------
    prefix : str
        Base PV address for all related records
    
    name : str
        Alias for the device

    z : float, optional
        Z position along the beamline

    beamline : str, optional
        Three character abbreviation for the specific beamline the device is on

    Attributes
    ----------
    state : str
        Either ``inserted``, ``unknown`` or ``removed``
    """
    state = LoggingPropertyMachine(DeviceStateMachine)

    SUB_DEV_CH = 'device_state_changed'
    _SUB_CP_CH = StateComponent.SUB_CP_CH

    _default_sub = SUB_DEV_CH

    def __init__(self, prefix, name=None, read_attrs=None,
            configuration_attrs=None, z=np.nan, beamline=None):

        #Instantiate all Opyhd signals
        super().__init__(prefix, name=name,
                         read_attrs=read_attrs,
                         configuration_attrs=configuration_attrs)

        #Make a logger for the device
        self.log = logging.getLogger('device_{}'.format(self.name))
        self.log.setLevel(logging.DEBUG)

        #Location identification
        if z is not None:
            self._z        = z

        if beamline is not None:
            self._beamline = beamline

        #Link update method with StateComponent callback 
        self.subscribe(self._update, event_type=self._SUB_CP_CH, run=True)




    @property
    def blocking(self):
        """
        Whether device has the potential to block the beam, this is True if
        either the state is ``unknown`` or ``inserted``
        """
        return (self.state == 'inserted' or self.state == 'unknown')


    @property
    def inserted(self):
        """
        Report if the device is inserted
        """
        return self.state == 'inserted'


    @property
    def removed(self):
        """
        Report if the device is removed
        """
        return self.state == 'removed'


    @property
    def output(self):
        """
        The output of the device in a tuple ``(beamline, transmission)``
        """
        if self.inserted:
            output = self.transmission

        elif self.state == 'unknown':
            output = np.nan

        else:
            output = 1.

        return (self.destination, output)


    def _setup_move(self, state, finished_cb=None, timeout=None):
        """
        Setup a Status object for a status change request
        """ 
        def finished():
            return self.state == state

        status = DeviceStatus(self, done=finished(),  timeout=timeout)

        def cb(*args, **kwargs):
            logger.debug('Checking if device has finished move')
            if finished():
                logger.debug('Device has completed the move')
                status._finished(success=True)
                if finished_cb is not None:
                    finished_cb()

        self.subscribe(cb, event_type=self.SUB_DEV_CH, run=False)
        status.finished_cb = partial(self.clear_sub, cb)

        return status



    def insert(self, timeout=None, finished_cb=None):
        """
        Insert the device into the beam path

        Returns
        -------
        DeviceStatus
        """
        return self._setup_move('inserted',
                                timeout=timeout,
                                finished_cb=finished_cb,
                               )


    def remove(self, timeout=None, finished_cb=None):
        """
        Remove the device into the beam path
        """
        return self._setup_move('removed',
                                timeout=timeout,
                                finished_cb=finished_cb,
                               )


    def _repr_info(self):
        yield ('prefix',   self.prefix)
        yield ('name',     self.name)
        yield ('z',        self.z)
        yield ('beamline', self.beamline)


    def _update(self, *args, timestamp=None,
                value=None, old_value=None,
                obj=None, **kwargs):
        """
        Callback to update underlying device StateMachine
        """
        logger.debug('Updating device {} based on updated ' 
                     'signal {}'.format(self, obj.name))

        #Grab cached states from components
        states = [(attr,cpt.state) for (attr,cpt) in self._sig_attrs.items()
                  if isinstance(cpt, StateComponent)]

        #Assume unknown state
        state = 'unknown'

        #Single unknown state
        if 'unknown' in [state for (attr, state) in states]:
            reason  = 'One or more components reporting unknown states'

        else:
            #Remove defered states
            known = [(attr,state) for (attr,state) in states
                     if state != 'defer']

            #If not state specifies
            if not known:
                reason = 'No component is in a definite state'

            #If multiple known states
            elif len(known) > 1:
                reason = 'Multiple conflicting components' 

            #A significant state
            else:
                (attr, state)  =  known[0]
                reason =  'Component {} moved to a state {}'.format(attr,
                                                                    state)
        #Log reasoning
        logger.debug(reason)

        #Change state machine if neccesary
        if state != self.state:
            self.state, old_value = state, self.state
            self._run_subs(sub_type  = self.SUB_DEV_CH,
                           old_value = old_value,
                           value     = self.state)

        else:
            logger.debug('Component states changed but overall '
                          'Device state remains {}'.format(self.state))


    __hash__ = Device.__hash__

    def __eq__(self, *args, **kwargs):
        try:
            return ((self.name, self.prefix, self.z)
                    == (args[0].name, args[0].prefix, args[0].z))

        except AttributeError:
            return super().__eq__(*args, **kwargs)
