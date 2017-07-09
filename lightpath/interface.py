"""
The Lightpath application depends on an a specific API for devices. For maximum
flexibility, and in order to avoid duplicating object implementations, any
object can be entered into the path as long as it agrees with one of the
interfaces below.

The :class:`.LightInterface` covers the majority of LCLS devices. While the
logical implementation of reading PVs and updating the reported state of the
device is up to the object to implement, the lightpath will count on these
functions to be accurate in order to determine the state of the beamline as a
whole. :class:`.LightInterface` can be used for any object that enters the
beam, regardless of whether it fully stops photons, for example an IPIMB target
would still use this interface. The only exception is devices that have the
potential that mark the transition from one beamline to another. These device
will use the :class:`.BranchingInterface` For instance the XCS LODCM when the
crystal is removed will allow beam to pass through to CXI.  However, when
inserted, a portion of the beam is sent to XCS.

The lightpath also surveys the devices for an attribute ``mps``. It is expected
that if a device is in the MPS system, this attribute will return a sub-device
that uses the :class:`.MPSInterface`
"""
############
# Standard #
############
import abc

###############
# Third Party #
###############
from ophyd.device import ComponentMeta

##########
# Module #
##########


class LightInterface(ComponentMeta, abc.ABCMeta):
    """
    Interface for a basic lightpath device
    """
    @abc.abstractproperty
    def z(self):
        """
        Z position along the beamline in meters
        """
        raise AttributeError

    @abc.abstractproperty
    def beamline(self):
        """
        Specific beamline the device is on
        """
        raise AttributeError


    @abc.abstractproperty
    def transmission(self):
        """
        Approximate transmission percentage of X-rays through device. Most
        devices will have 0.0 transmission, as in they block the beam
        completely
        """
        raise AttributeError


    @abc.abstractproperty
    def inserted(self):
        """
        Report if the device is currently inserted into the beam
        """
        raise AttributeError


    @abc.abstractproperty
    def removed(self):
        """
        Report if the device is currently removed from the beam
        """
        raise AttributeError


    @abc.abstractmethod
    def remove(self, wait=False, timeout=None, finished_cb=None):
        """
        Remove the device from the beampath

        Parameters
        ----------
        wait : bool, optional
            Wait for the move to complete

        timeout : float, optional
            Maximum time to wait for move to complete

        finished_cb : callable, optional
            Callable to run when the move is complete

        Returns
        -------
        status : ophyd.Status
            Status object linked with completion of move
        """
        raise NotImplementedError


    @abc.abstractmethod
    def subscribe(cb, event_type=None, run=False, **kwargs):
        """
        Subscribe a callback function to run when the device changes state

        Parameters
        ----------
        cb : callable
            Function to be run upon change

        event_type : str, optional
            Type of event the function will be called after

        run : bool, optional
            Run the callable immediately or wait for an event.
        """
        raise NotImplementedError


class BranchingInterface(LightInterface):
    """
    Interface for a branching device
    """
    @abc.abstractproperty
    def destination(self):
        """
        Current destinations of the branching device. Should always be returned
        as a list to accomodate branches that can send beam to multiple
        positions
        """
        raise AttributeError


    @abc.abstractproperty
    def branches(self):
        """
        List of possible beamlines the device is available to send photons
        """
        raise AttributeError



class MPSInterface(ComponentMeta, abc.ABCMeta):
    """
    Interface for MPS device
    """
    @abc.abstractproperty
    def faulted(self):
        """
        Boolean of whether MPS is faulted or not
        """
        raise AttributeError

    
    @abc.abstractproperty
    def veto_capable(self):
        """
        Whether the device causes downstream faults to be ignored
        """
        raise AttributeError


    @abc.abstractproperty
    def bypassed(self):
        """
        Bypass state of the MPS bit
        """
        raise AttributeError



