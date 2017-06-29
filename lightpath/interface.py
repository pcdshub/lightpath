"""
Define standard interfaces for basic lightpath devices and branching patterns
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
        Z position along the beamline
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
        Approximate transmission of X-rays through device
        """
        raise AttributeError


    @abc.abstractproperty
    def inserted(self):
        """
        Report if the device is inserted into the beam
        """
        raise AttributeError


    @abc.abstractproperty
    def removed(self):
        """
        Report if the device is inserted into the beam
        """
        raise AttributeError


    @abc.abstractmethod
    def remove(self, timeout=None, finished_cb=None):
        """
        Remove the device from the beampath
        """
        raise NotImplementedError


    @abc.abstractmethod
    def subscribe(cb, event_type=None, run=False, **kwargs):
        """
        Subscribe a callback function to run when the device changes state
        """
        raise NotImplementedError


class BranchingInterface(LightInterface):

    @abc.abstractproperty
    def destination(self):
        """
        Current destination of the branching device
        """
        raise AttributeError


    @abc.abstractproperty
    def branches(self):
        """
        List of possible beamlines the device is available to send photons
        """
        raise AttributeError


