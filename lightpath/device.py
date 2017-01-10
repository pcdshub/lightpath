import time
import logging
import textwrap

logger = logging.getLogger(__name__)

class States:
    """
    Four way state
    """
    inserted   = 'inserted'
    removed    = 'removed'
    partially  = 'partially inserted'
    unknown    = 'unknown'


class StatePV(object):
    """
    Object to handle a device related to an objects state
    """
    def __init__(self, suffix=None, add_prefix=True, doc=None):
        self.suffix = suffix
        self.prefix = add_prefix
        self.doc    = doc

    def add_prefix(self, instance, suffix): 


class LightDevice(object):
    """
    Base class to represent a device along the Lightpath

    The main function of this class is to define a standard API for further
    device classes to reuse based on their individual states. Each class
    that inherits this as its base should reimplement the following methods;     
    :meth:`.insert`, :meth:`.remove`, :meth:`.home`, and :meth:`.update. Also,
    if the device has a more complex relationship with the beam than blocking
    or not, it may be neccesary to reimplement :meth:`.transmission` 

    Parameters
    ----------
    alias : str
        Alias for the device

    z : float
        Z position along the beamline

    beamline : str
        Three character abbreviation for the specific beamline the device is on
    """
    _last_home = None

    def __init__(self, alias, base, z=-1.0, beamline=None):
        self._alias    = alias
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


    def insert(self):
        """
        Insert the device into the beam path
        """
        self._state = States.inserted


    @property
    def inserted(self):
        """
        Report of the device is inserted
        """
        if self.state in (States.inserted, States.partially):
            return True

        else:
            return False


    def remove(self):
        """
        Remove the device into the beam path
        """
        self._state = States.removed


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
        if self.state == States.inserted
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
        self._last_home = time.ctime()


    def update(self):
        """
        Update the current state of the device

        .. note::
            This method is used as a callback for a devices state PVS
        """
        pass 


   
