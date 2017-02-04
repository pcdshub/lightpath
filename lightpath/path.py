import copy
import logging
import numpy as np
from .device import LightDevice, MPSDevice
from .utils  import timeout, CoordinateError, MotionError

logger = logging.getLogger(__name__)

class BeamPath:
    """
    Represents a straight line of devices along the beamline

    Parameters
    ----------
    devices : :class:`.LightDevice`
        Arguments are interpreted as LightDevices along a common beamline.
    """
    def __init__(self, *devices):
        #Check types and positions
        for dev in devices:
            if not isinstance(dev, LightDevice):
                raise TypeError('{!r} is not a valid LightDevice'.format(dev))

            if np.isnan(dev.line_position):
                CoordinateError('Device {!r} is reporting a non-existant beamline '\
                                'position, its coordinate was not properly '\
                                'initialized.'.format(dev))

        #Sort by position downstream to upstream
        self.devices = sorted(devices, key =lambda dev : dev.line_position)


    @property
    def start(self):
        """
        First device along the path
        """
        return self.devices[0]


    @property
    def finish(self):
        """
        Final device along the path
        """
        return self.devices[-1]


    @property
    def inserted_devices(self):
        """
        A list of devices that are currently blocking the beam
        or are in unknown positions
        """
        #Used .removed instead of .inserted for `unknown devices`
        return [device for device in self.devices if not device.removed]


#    @property
#    def faulted_devices(self):
#        """
#        A list of faulted MPS devices
#        """
#        return [device for device in self.devices
#                if isinstance(device,MPSDevice) and device.faulted]
#
#
#    @property
#    def veto_devices(self):
#        """
#        A list of MPS veto devices along the path
#        """
#        return [device for device in self.devices
#                if isinstance(device,MPSDevice) and device.vetoable]


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


    def device_scan(self, timeout=None, reversed=False, ignore_devices=None):
        """
        Insert and remove each device one by one
        """

        #Setup scanned device list
        if ignore_devices:
            devices, ignore_devices = self._ignore(ignore_devices)

        else:
            devices = copy.copy(self.devices)
            ignore_devices = []

        #If you want to go from upstream to downstream
        if reversed:
            devices.reverse()


        #Iterate through the devices
        logger.info('Scanning along the beampath {} ...'.format(self))
        for device in devices:

            #Insert the device 
            ignore_devices.append(start)
            start.insert()
            t0 = time.time()

            #Clear the beampath
            self.clear(wait=True, timeout=timeout,
                       ignore_devices=ignore_devices)

            #Check device has finished move
            if not device.inserted:
                logger.debug('Waiting for {} to be '\
                             'inserted into the beam ...'.format(device))

               while not timeout is None and time.time() > t0:
                    time.sleep(0.05)

            #Yield the current device in the beam
            yield device

            #Remove the device from ignored 
            ignore_devices.pop(device)


    def clear(self, wait=False, timeout=None, ignore_devices=None):
        """
        Clear the beampath of all obstructions

        Parameters
        ----------
        wait : bool
            Wait for all devices to complete their motion

        timeout : float, optional
            Duration to wait for device movements

        ignore_devices : LightDevice or iterable, optional
            Leave devices in their current state without removing them

        Raises
        ------
        MotionError:
            If one or more of the devices fails to complete its move in the
            time alotted
        """
        logger.info('Clearing beampath {} ...'.format(self))

        #Assemble device list
        if ignore_devices:
            target_devices, ignored = self._ignore(ignore_devices)
        else:
            target_devices = self.devices

        #Remove devices
        map(lambda device : device.remove(), target_devices)

        #Wait parameters
        if wait:

            logger.debug('Waiting for all devices to be '\
                         'removed from the beampath {} ...'.format(self))

            if all([device.removed for device in target_devices]):
                logger.info('{} has been successfully cleared.'.format(self))

            else:
                raise MotionError('Failed to remove all devices '\
                                  'from the beampath in {}s.'.format(timeout))


        return status


    def join(self, *beampaths):
        """
        Join other beampaths with the current one

        Parameters
        ----------
        beampaths : arguments
            A list of beampaths to join into a complete path, order is
            irrelavant

        Returns
        -------
        BeamPath : :class:`.BeamPath`
            A new object with all of the path devices

        Raises
        ------
        TypeError:
            Raised if a non-BeamPath object is supplied
        """
        return BeamPath.join(self,*beampaths)




    @classmethod
    def from_join(cls, *beampaths):
        """
        Join other beampaths with the current one

        Parameters
        ----------
        beampaths : arguments
            A list of beampaths to join into a complete path, order is
            irrelavant

        Returns
        -------
        BeamPath : :class:`.BeamPath`
            A new object with all of the path devices

        Raises
        ------
        TypeError:
            Raised if a non-BeamPath object is supplied
        """
        if not all(isinstance(bp,BeamPath) for bp in beampaths):
            raise TypeError('Can not join non-BeamPath object')

        devices = [device for device in path.devices for path in beampaths]


        return BeamPath(*set(devices))


    def _ignore(self, ignore_devices):
        """
        Assemble list of available devices with some exclusions
        """
        if isinstance(ignore_devices, LightDevice):
            ignore_devices = [ignore_devices]

        if any([not isinstance(device, LightDevice)
                for device in ignore_devices]):
            raise TypeError('Ignored devices must be a LightDevice object')

        target_devices = [device for device in self.devices
                          if device not in ignore_devices]

        return target_devices, ignore_devices


    def _repr_info(self):
        yield('start',  self.start.line_position)
        yield('finish', self.finish.line_position)
        yield('devices', len(self.devices)


    def __repr__(self):
        info = self._repr_info()
        info = ','.join('{}={!r}'.format(key, value) for key, value in info)
        return '{!r}({})'.format(self.__class__, info)   
 
