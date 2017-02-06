import sys
import copy
import logging
import numpy as np

from ophyd.ophydobj import OphydObject
from prettytable import PrettyTable

from .device import LightDevice
from .utils  import CoordinateError, MotionError

logger = logging.getLogger(__name__)

class BeamPath(OphydObject):
    """
    Represents a straight line of devices along the beamline

    Parameters
    ----------
    devices : :class:`.LightDevice`
        Arguments are interpreted as LightDevices along a common beamline.
    """
    SUB_PTH_CHNG = 'beampath_changed'

    def __init__(self, *devices):
        #Check types and positions
        for dev in devices:
            if not isinstance(dev, LightDevice):
                raise TypeError('{!r} is not a valid LightDevice'.format(dev))

            #Ensure positioning is physical
            if np.isnan(dev.z) or dev.z < 0.:
                CoordinateError('Device {!r} is reporting a non-existant beamline '\
                                'position, its coordinate was not properly '\
                                'initialized.'.format(dev))

        #Sort by position downstream to upstream
        self.devices = sorted(devices, key =lambda dev : dev.z)

        #Add callback to device state change
        for d in self.devices:
            d.subscribe(self._device_moved,
                        event_type=d.SUB_DEV_CH,
                        run=False)

        #Add callback here!
        self.mirrors = [d for d in self.devices if d.branching]


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
    def range(self):
        """
        Range of Z positions the path covers
        """
        return self.start.z, self.finish.z


    @property
    def device_names(self):
        """
        Device names fo devices in the BeamPath
        """
        return [device.name for device in self.devices]


    @property
    def device_prefixes(self):
        """
        The prefix names for all devices in the BeamPath
        """
        return [device.prefix for device in self.devices]


    @property
    def blocking_devices(self):
        """
        A list of devices that are currently blocking the beam
        or are in unknown positions
        """
        block = []

        for pos, device in enumerate(self.devices):
            if device.branching:
                try:

                    if self.devices[i+1].beamline != device.beamline:
                        block.append(device)

                except IndexError:
                    logger.debug('Branching device is last in beamline')

            elif device.blocking and not device.passive:
                block.append(device)

        return block

    
    @property
    def state(self):
        """
        Current state of the path devices
        
        .. todo::

            Both this and restore state should use ``configuration_attrs`` from
            Ophyd
        """
        return dict([(device.name, device.state) for device in self.devices])


    def restore_state(self, state):
        """
        Restore a beampath configuration from state
        """
        def restore(dev, st):
            if state == 'unknown':
                logger.error('Can not restore {} to an unknown state'
                             ''.format(dev))
                status = None

            elif st == 'removed':
                status = dev.remove()

            elif st == 'unknown':
                status = dev.insert()

            else:
                raise ValueError('Unrecognized state {}'.format(st))

        return [restore(d,s) for d,s in state.items()]


    def show_devices(self, state=None, file=sys.stdout):
        """
        Print a table of the devices along the beamline

        Parameters
        ----------
        state : str
            Show only devices in a specific state, 'inserted', 'removed',
            'unknown'

        file : file-like object
            File to place table
        """
        #Initialize Table
        pt = PrettyTable(['Name', 'Prefix', 'Position', 'Beamline','State'])

        #Adjust Table settings
        pt.align('r')
        pt.align['Name'] = 'l'
        pt.float_format  = '8.5'

        #Narrow to state
        if state:
            d_list = [d for d in self.devices if d.state == state]

        else:
            d_list = self.devices

        #Add info
        for d in d_list:
            pt.add_row([d.name, d.prefix, d.z, d.beamline, d.state])

        #Show table
        print(pt, file=file)


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
        if not self.blocking_devices:
            return None

        else:
            return self.blocking_devices[0]


    @property
    def cleared(self):
        """
        Whether beamline is clear of any devices
        """
        return any(self.blocking_devices)


#    def device_scan(self, timeout=None, reversed=False, ignore_devices=None):
#        """
#        Insert and remove each device one by one
#        """
#
#        #Setup scanned device list
#        if ignore_devices:
#            devices, ignore_devices = self._ignore(ignore_devices)
#
#        else:
#            devices = copy.copy(self.devices)
#            ignore_devices = []
#
#        #If you want to go from upstream to downstream
#        if reversed:
#            devices.reverse()
#
#
#        #Iterate through the devices
#        logger.info('Scanning along the beampath {} ...'.format(self))
#        for device in devices:
#
#            #Insert the device 
#            ignore_devices.append(start)
#            start.insert()
#            t0 = time.time()
#
#            #Clear the beampath
#            self.clear(wait=True, timeout=timeout,
#                       ignore_devices=ignore_devices)
#
#            #Check device has finished move
#            if not device.inserted:
#                logger.debug('Waiting for {} to be '\
#                             'inserted into the beam ...'.format(device))
#
#               while not timeout is None and time.time() > t0:
#                    time.sleep(0.05)
#
#            #Yield the current device in the beam
#            yield device
#
#            #Remove the device from ignored 
#            ignore_devices.pop(device)


    def clear(self, wait=False, timeout=None,
              passive=False, ignore=None):
        """
        Clear the beampath of all obstructions

        Parameters
        ----------
        wait : bool
            Wait for all devices to complete their motion

        timeout : float, optional
            Duration to wait for device movements

        ignore: LightDevice or iterable, optional
            Leave devices in their current state without removing them

        passive : If True, passive devices will also be reviewed 
        """
        logger.info('Clearing beampath {} ...'.format(self))

        #Assemble device list
        target_devices, ignored = self._ignore(ignore, passive=passive)

        #Remove devices
        status = [device.remove(timeout=timeout) for device in target_devices]

        #Wait parameters
        if wait:
            logger.debug('Waiting for all devices to be '\
                         'removed from the beampath {} ...'.format(self))

            for s in status:
                print('Waiting for {} to be done ...'.format(s))
                wait(s, timeout=timeout)
                print('Completed')

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


    def split(self, z=None, device=None):
        """
        Split the beampath producing two new BeamPath objects either by a
        specific position or a devices location
        
        Parameters
        ----------
        z : float
            Z position to split the paths

        device  : LightDevice, name, or base PV
            The specified device will be the first device in the second
            :class:`.BeamPath` object
        
        Returns
        -------
        BeamPath, BeamPath
            Two new beampath instances
        """
        if not z or device:
            raise ValueError("Must supply information where to split the path")

        #Grab the z if given a device
        if device:
            z = self._device_lookup(device).z

        if z< self.range[0] and z<self.range[1]:
            raise ValueError("Split position  {} is not within the range of "
                             "the path.".format(z))

        return (BeamPath(*[d for d in devices if d.z <  z]),
                BeamPath(*[d for d in devices if d.z >= z]),
               )


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


    def _ignore(self, ignore_devices, passive=False):
        """
        Assemble list of available devices with some exclusions
        """
        #Always ignore mirrors
        ignore = copy.copy(self.mirrors)

        #Add passive devices to ignored
        if not passive:
            ignore.extend([d for d in self.devices if d.passive])

        #Add ignored devices
        if not isinstance(ignore_devices, (tuple, list, set)):
            ignore.append(self._device_lookup(ignore_devices))

        else:
            ignore.extend([self._device_lookup(d) for d in ignored_devices])

        #Grab target devices
        target_devices = [device for device in self.devices
                          if device not in ignore_devices]

        return target_devices, ignore_devices


    def _device_lookup(self, device):
        """
        Lookup a device by name or prefix
        """
        #Check if given a device name
        if device in self.device_names:
            pos    = self.device_names.index(device)
            device = self.devices[pos]

        #Check if given a device prefix
        elif device in self.device_prefixes:
            pos    = self.device_prefixes.index(device)
            device = self.devices[pos]


        if device not in self.devices:
            raise ValueError("Could not find device {} in the path"
                             "".format(device))
        return device


    def _device_moved(self, *args, obj=None):
        """
        Run when a device changes state
        """
        #Maybe this should introspect and see if beampath state changes
        self._run_subs(*args, 
                       sub_type=self.SUB_PTH_CHNG,
                       device = obj,
                       **kwargs)


    def _repr_info(self):
        yield('start',  self.start.z)
        yield('finish', self.finish.z)
        yield('devices', len(self.devices))


    def __cmp__(self, *args, **kwargs):
        if arg[0] is NOne:
            return 1

        return cmp(self.devices, arg[0].devices)
