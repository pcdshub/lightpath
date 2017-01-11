import logging
from .device import LightDevice
from .utils  import CoordinateError, TimeoutError

logger = logging.getLogger(__name__)

class BeamPath(object):
    """
    Represents a straight line of devices along the beamline

    Parameters
    ----------
    devices : :class:`.LightDevice`
        Arguments are interpreted as LightDevices along a common beamline.
    """
    def __init__(self, *devices, input=None):
        #Check types and positions
        for dev in devices:
            if not isinstance(dev, LightDevice):
                raise TypeError('{!r} is not a valid LightDevice'.format(dev))

            if dev.line_position < 0.:
                CoordinateError('Device {!r} is reporting a negative beamline '\
                                'position, its coordinate was not properly '\
                                'initialized.'.format(dev))

        #Sort by position downstream to upstream
        self.devices = sorted(devices, key =lambda dev : dev.line_position)


    @property
    def inserted_devices(self):
        """
        A list of devices that are currently blocking the beam
        """
        #Used .removed instead of .inserted for `unknown devices`
        return [device for device in self.devices if not device.removed]


    @property
    def impediment(self):
        """
        First blocking device along the path
        """
        if not self.inserted_devices:
            return None

        else:
            return self.inserted_devices[0]


    @property
    def cleared(self):
        """
        Whether beamline is clear of any devices
        """
        return any(self.inserted_devices)


    def clear(self, wait=False, timeout=None):
        """
        Clear the beampath of all obstructions
        """
        #Return immediately if cleared
        if self.cleared:
            return
        
        #Clear devices 
        map(lambda device : device.remove(), self.blocking_devices)
        t0 = time.time()

        #Wait parameters
        if wait:            
            def time_exceeded():
                return not timeout is None and (time.time() - t0) > timeout

            while not self.cleared not time_exceeded():
                time.sleep(0.05)

            return
            
