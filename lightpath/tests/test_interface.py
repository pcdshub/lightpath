############
# Standard #
############

###############
# Third Party #
###############
from ophyd import Device

##########
# Module #
##########
from lightpath.interface import LightInterface

class BasicDevice(Device, metaclass=LightInterface):

    @property
    def z(self):
        """
        Z position along the beamline
        """
        return None

    @property
    def beamline(self):
        """
        Specific beamline the device is on
        """
        return None


    @property
    def transmission(self):
        """
        Approximate transmission of X-rays through device
        """
        return None


    @property
    def inserted(self):
        """
        Report if the device is inserted into the beam
        """
        return None


    @property
    def removed(self):
        """
        Report if the device is inserted into the beam
        """
        return None


    def remove(self, timeout=None, finished_cb=None):
        """
        Remove the device from the beampath
        """
        pass


    def subscribe(cb, event_type=None, run=False, **kwargs):
        """
        Subscribe a callback function to run when the device changes state
        """
        pass


class BasicBranching(Device, metaclass=LightInterface):
    @property
    def z(self):
        """
        Z position along the beamline
        """
        return None

    @property
    def beamline(self):
        """
        Specific beamline the device is on
        """
        return None


    @property
    def transmission(self):
        """
        Approximate transmission of X-rays through device
        """
        return None


    @property
    def inserted(self):
        """
        Report if the device is inserted into the beam
        """
        return None


    @property
    def removed(self):
        """
        Report if the device is inserted into the beam
        """
        return None


    def remove(self, timeout=None, finished_cb=None):
        """
        Remove the device from the beampath
        """
        pass


    def subscribe(cb, event_type=None, run=False, **kwargs):
        """
        Subscribe a callback function to run when the device changes state
        """
        pass


    def branching(self):
        return None


    def destination(self):
        return None



def test_basic_interface():
    device = BasicDevice("base")
    #Check that our class is a LightInterface type 
    assert type(BasicDevice) == LightInterface
    #Check that the device is an ophyd device
    assert isinstance(device, Device)


def test_branching_interface():
    device = BasicBranching("base")
    #Check that our class is a LightInterface type 
    assert type(BasicBranching) == LightInterface
    #Check that the device is an ophyd device
    assert isinstance(device, BasicBranching)
