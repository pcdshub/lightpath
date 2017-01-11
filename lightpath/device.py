import time
import logging
import textwrap
from collections import OrderedDict

from psp import PV
from . status import Status

logger = logging.getLogger(__name__)

class States:
    """
    Four way state
    """
    inserted   = 'inserted'
    removed    = 'removed'
    partially  = 'partially inserted'
    unknown    = 'unknown'

class Component(object):
    """
    Object to handle a device related to an objects state
    """
    def __init__(self, suffix, add_prefix=True, update=False):
        self.suffix     = suffix
        self.attr       = None #Set later by Device
        self.add_prefix = add_prefix
        self.update     = update


    def maybe_add_prefix(self, instance, suffix):
        """
        Add the suffix to the devices prefix
        """ 
        if instance.prefix:        
            return '{}{}'.format(instance.prefix, suffix)

        return suffix

    
    def create_component(self, instance):
        """
        Create a component PV for the instance
        """
        if self.add_prefix:
            pv_name = self.maybe_add_prefix(instance, self.suffix)

        else:
            pv_name = suffix
        
        pv_inst = PV(pv_name, initialize=True, monitor=True) 
        
        if self.update:
            self.add_monitor_callback(instance.update, once=False)

        return pv_inst


    def __repr__(self):
        return 'PV({},update={!r})'.format(self.suffix, self.update)  


    def __get__(self, instance, owner):
        if instance is None:
            return self

        return instance._cpts[self.attr]


    def __set__(self, instance, owner):
        raise RuntimeError('Use .put()')


class Device(type):
    """
    Creates attributes for Components class definition
    """
    def __new__(cls, name, bases, clsdict):
        clsobj = super(Device, cls).__new__(cls, name, bases, clsdict)


        #These attributes are reserved for LightDevice functionality and 
        #can not be used as component names
        RESERVED_ATTRS = ['line_position', 'alias', 'prefix', 'beamline',
                          'insert', 'inserted', 'remove', 'removed', 'state',
                          'transmission', 'home', 'update']


        #Check names
        clsobj._cpts = OrderedDict()
        for attr, value in clsdict.items():
            if isinstance(value, Component):
                if attr in RESERVED_ATTRS:
                    raise TypeError('The attribute name {} is part of the '\
                                    'LightDevice interface and can not be '\
                                    'used as a name of a component. Choose '\
                                    'a different name'.format(attr))

                if attr.startswith('_'):
                    raise TypeError('Attribute name can not start with _ '\
                                    'because of the risk of overwriting '\
                                    'an existing private attribute. Choose '\
                                    'a different name')
                
                clsobj._cpts[attr] = value
                
        #Set the attributes
        for cpt_attr, cpt in clsobj._cpts.items():
            cpt.attr = cpt_attr
            setattr(clsobj, cpt_attr, cpt.create_component(clsobj))


        return clsobj


class LightDevice(object):
    """
    Base class to represent a device along the Lightpath

    The main function of this class is to define a standard API for further
    device classes to reuse based on their individual states. Each class
    that inherits this as its base should reimplement the following methods;     
    :meth:`.insert`, :meth:`.remove`, :meth:`.home`, and :meth:`.update`. Also,
    if the device has a more complex relationship with the beam than blocking
    or not, it may be neccesary to reimplement :meth:`.transmission`. Finally,
    if the device is capable of measuring the presence of beam, rewriting the
    :meth:`.verify` can be overwritten as well to be used by the LightPath client
    to check the predicted beamline state

    Parameters
    ----------
    alias : str
        Alias for the device

    prefix : str
        Base PV address for all related records

    z : float, optional
        Z position along the beamline

    beamline : str, optional
        Three character abbreviation for the specific beamline the device is on
    """
    __metaclass__ = Device
    _last_home    = None
    
    def __init__(self, alias, prefix=None, z=-1.0, beamline=None):
        self._alias    = alias
        self._prefix   = prefix
        self._z        = z
        self._beamline = None
        self._state    = States.unknown 


    #Set these as properties to make them write-only
    @property
    def line_position(self):
        """
        Z position along the beamline 
        """
        return self._z


    @property
    def alias(self):
        """
        Alias of the device
        """
        return self._alias


    @property
    def beamline(self):
        """
        Specific beamline the device is on
        """
        return self._beamline


    @property
    def prefix(self):
        """
        Base PV prefix for the device
        """
        return self._prefix


    def insert(self, timeout=None):
        """
        Insert the device into the beam path
        """
        logger.debug('Inserting device {} ...'.format(self))
   
 
    @property
    def inserted(self):
        """
        Report if the device is inserted
        """
        if self.state in (States.inserted, States.partially):
            return True

        else:
            return False


    def remove(self):
        """
        Remove the device into the beam path
        """
        logger.debug('Removing device {} ...'.format(self))


    @property
    def removed(self):
        """
        Report if the device is removed
        """
        if self.state == States.removed:
            return True

        else:
            return False


    @property
    def state(self):
        """
        Current state of the device
        """
        return self._state


    @property
    def transmission(self):
        """
        Current transmission through the device
        
        This only needs to be reimplimented if the device needs to handle being
        partially blocked

        Returns
        -------
        transmission : float
            Current transmission through the device, if the state is unknown
            -1.0 is returned
        
        Raises
        ------
        NotImplementedError:
            If the device is ``partially`` blocking the beam or the
            :attr:`.state` is an unrecognized value
        """
        if self.state == States.inserted:
            return 0.

        elif self.state == States.removed:
            return 100.0

        elif self.state == States.unknown:
            return -1.0

        else:
            raise NotImplementedError('Transmission can not be '
                                      'calculated for state {}'.format(self.state))


    def home(self):
        """
        Home the device
        """
        logger.debug('Homing device {} ...'.format(self))
        self._last_home = time.ctime()


    def verify(self):
        """
        Verify that the beam is actually incident upon the device
        """
        raise NotImplementedError('{!r} does not have a method to verify '\
                                  'the beam location'.format(self))


    def update(self):
        """
        Update the current state of the device

        .. note::

            This method is used as a callback for a devices state PV
        """
        logger.debug('Updating state for device {} ...'.format(self))


    def _repr_info(self):
       yield ('alias', self.alias)
       yield ('position', self.line_position)
       yield ('beamline', self.beamline)

 
    def __repr__(self):
        info = self._repr_info()
        info = ','.join('{}={!r}'.format(key, value) for key, value in info)
        return '{!r}({})'.format(self.__class__, info)   


class MPSDevice(LightDevice):
    """
    A LightPath Device that is also protected by MPS

    Parameters
    ----------
    alias : str
        Alias for the device

    prefix : str
        Base PV address for all related records

    mps_prefix : str
        Base PV address for all related MPS records

    veto : bool, optional
        Whether it is considered an MPS vetodevice 
 
    z : float, optional
        Z position along the beamline

    beamline : str, optional
        Three character abbreviation for the specific beamline the device is on

    """
    def __init__(self, alias, mps_prefix=None, veto=False,
                 prefix=None, z=-1.0, beamline=None):
        super(MPSDevice, self).__init__(alias, prefix=prefix, z=z, beamline=beamline)

        #Some additional attributes
        self.vetoable  = veto
        self._faulted  = False
        self._bypassed = False

        #Raise error if not properly initialized with MPS
        if not mps_prefx:
            raise ValueError('MPSDevice must be provided a base PV description '\
                             'for the pertinent MPS records to be monitored.')

        #Start monitoring
        self._is_ok  = PV('{}_MPSC',initialize=True, monitor=True)
        self._bypass = PV('{}_BYPS',initialize=True, monitor=True)

        map(lambda pv : pv.add_monitor_callback(self._state_change),
            [self._bypass, self._fault])

        #Establish starting state
        self._state_change()


    @property
    def faulted(self):
        """
        Whether device is currently in a faulted state or not
        """
        return self._faulted


    def insert(self):
        """
        Insert the device into the beamline
        """
        super(MPSDevice,self).remove()
        if not self.vetoable:
            logger.warning('Inserting MPS device {}, '\
                           'this may cause a fault ...'.format(self)) 
        

    def remove(self):
        """
        Remove the device from the beamline
        """
        super(MPSDevice,self).remove()
        if self.vetoable:
            logger.warning('Removing MPS veto device {}, '\
                           'this may cause a fault ...'.format(self)) 


    def _state_change(self, e=None)
        """
        Callback for changes to the MPS state
        """
        if self._bypassed.get():
            logger.info('Device {} has been bypassed'.format(self))
            self._faulted = False

        elif not self._is_ok.get():
            logger.error('Device {} is reporting an MPS fault'.format(self))
            self._faulted = True

        else:
            self._faulted = False

 

