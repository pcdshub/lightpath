"""
The :class:`.BeamPath` is the main abstraction for the lightpath module,
grouping together a set of devices using the :class:`.LightInterface` and
representing the path between them as single object. While the manipulation of
each of these object should be done at the device level, the
:meth:`.BeamPath.clear` does provide a powerful tool to quickly change the
status of the path.

The :class:`.BeamPath` object is also not meant to be a rigid representation,
:meth:`.BeamPath.split` and :meth:`.BeamPath.join` both allow for slicing and
combining of different areas of the LCLS beamline. However, keep in mind that
the path only knows the state of the devices it contains, so certain methods
might not return an accurate representation of reality if an upstream device is
affecting the beam.
"""
####################
# Standard Library #
####################
import logging
from collections import Iterable

####################
#    Third Party   #
####################
import numpy as np
from prettytable    import PrettyTable
from ophyd.ophydobj import OphydObject
from ophyd.status   import wait as status_wait

####################
#     Package      #
####################
from .errors import CoordinateError


logger = logging.getLogger(__name__)

class BeamPath(OphydObject):
    """
    Represents a straight line of devices along the beamline

    The devices given must be a continuous set all along the same beamline, or,
    multiple beamlines with appropriate reflecting devices in between. 

    Parameters
    ----------
    devices : :class:`.LightDevice`
        Arguments are interpreted as LightDevices along a common beamline.

    name = str, optional
        Name of the BeamPath

    Raises
    ------
    TypeError:
        If a non-LightDevice object is supplied

    CoordinateError:
        If a coordinate is not properly specified

    PathError:
        If multiple beamlines are present, with no reflecting device

    Attributes
    ----------
    minimum_transmission : float
        Minimum amount of transmission considered for beam presence
    """
    #Subscription Information
    SUB_PTH_CHNG     = 'beampath_changed'
    SUB_MPSPATH_CHNG = 'mpspath_changed'
    _default_sub     = SUB_PTH_CHNG
    #Transmission setting
    minimum_transmission = 0.1

    def __init__(self, *devices, name=None):
        super().__init__(name=name)
        self.devices = devices
        logger.debug("Configuring path %s with %s devices",
                     name, len(self.devices))
        #Sort by position downstream to upstream
        try:
            #Check types and positions
            for dev in self.path:
                #Ensure positioning is physical
                if np.isnan(dev.z) or dev.z < 0.:
                    raise CoordinateError('Device %r is reporting a '
                                          'non-existant beamline position, '
                                          'its coordinate was not properly '
                                          'initialized', dev)
                #Add callback here!
                dev.subscribe(self._device_moved,
                              run=False)
                #Add as attribute
                setattr(self, dev.name.replace(' ','_'), dev)

        except AttributeError as e:
            raise TypeError('One of the devices does not meet the ' 
                            'neccesary lightpath interface. Missing '
                            'attribute {}'.format(e))

    @property
    def branches(self):
        """
        Branching devices along the path
        """
        return [d for d in self.devices if getattr(d, 'branches', False)]

    @property
    def range(self):
        """
        Starting z position of beamline
        """
        return self.path[0].z, self.path[-1].z

    @property
    def path(self):
        """
        List of devices ordered by coordinates
        """
        return sorted(self.devices, key=lambda dev : dev.z)

    @property
    def blocking_devices(self):
        """
        A list of devices that are currently inserted or are in unknown
        positions. This includes devices downstream of the first
        :attr:`.impediment`
        """
        #Cache important prior devices
        prior         = None
        last_branches = list()
        block         = list()
        for device in self.path:
            #If we have switched beamlines
            if prior and device.beamline != prior.beamline:
                #Find improperly configured optics
                for optic in last_branches:
                    if device.beamline not in optic.destination:
                        block.append(optic)
                #Clear optics that have been evaluated
                last_branches.clear()

            #If our last device was an optic, make sure it wasn't required
            #to continue along this beampath
            elif (prior in last_branches
                and device.beamline in prior.branches
                and device.beamline not in prior.destination):
                block.append(last_branches.pop(-1))

            #Find branching devices and store
            #They will be marked as blocking by downstream devices
            if device in self.branches:
                last_branches.append(device)

            #Find inserted devices
            elif device.inserted and (device.transmission <
                                    self.minimum_transmission):
                block.append(device)
            #Find unknown devices
            elif not device.removed and not device.inserted:
                block.append(device)
            #Stache our prior device
            prior = device

        return block

    @property
    def incident_devices(self):
        """
        A list of devices the beam is currently incident on. This includes the
        current :attr:`.impediment` and any upstream devices that may be
        inserted but have more transmission than :attr:`.minimum_transmission`
        """
        inserted = [d for d in self.path if d.inserted]
        #Return an empty list instead of None
        if not inserted:
            return []
        #No blocking devices, all inserted devices incident
        elif not self.impediment:
            return inserted
        #Otherwise only return upstream of the impediment
        else:
            return [d for d in inserted if d.z <= self.impediment.z]

    def show_devices(self, file=None):
        """
        Print a table of the devices along the beamline

        Parameters
        ----------
        file : file-like object
            File to writable
        """
        #Initialize Table
        pt = PrettyTable(['Name', 'Prefix', 'Position', 'Beamline', 'Removed'])
        #Adjust Table settings
        pt.align = 'r'
        pt.align['Name'] = 'l'
        pt.align['Prefix'] = 'l'
        pt.float_format  = '8.5'
        #Add info
        for d in self.path:
            pt.add_row([d.name, d.prefix, d.z, d.beamline, str(d.removed)])
        #Show table
        print(pt, file=file)

    @property
    def veto_devices(self):
        """
        A list of MPS veto devices along the path
        """
        return [device for device in self.path
                if getattr(device, 'mps', None)
                and device.mps.veto_capable]

    @property
    def tripped_devices(self):
        """
        Devices who are both faulted and unprotected from the beam
        """
        ins_veto = [veto for veto in self.veto_devices if veto.inserted]

        if not ins_veto:
            return self.faulted_devices

        return [d for d in self.faulted_devices
                  if ins_veto[0].z > d.z]

    @property
    def faulted_devices(self):
        """
        A list of faulted MPS devices, this includes those protected by veto
        devices
        """
        return [device for device in self.path
                if getattr(device, 'mps', None)
                and device.mps.faulted
                and not device.mps.bypassed]

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
        Whether beamline is clear of any devices that are below the
        :attr:`.minimum_transmission`
        """
        return not any(self.blocking_devices)

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

        ignore: device or iterable, optional
            Leave devices in their current state without removing them

        passive : bool, optional
            If False, devices that are inserted but don't attenuate the beam
            below :attr:`.minimum_threshold` are ignored

        Returns
        -------
        statuses :
            Returns list of status objects returned by
            :meth:`.LightInterface.remove`
        """
        logger.info('Clearing beampath %s ...', self)
        #Assemble device list
        target_devices, ignored = self._ignore(ignore, passive=passive)
        #Remove devices
        logger.info('Removing devices along the beampath ...')
        status = [device.remove(timeout=timeout)
                  for device in target_devices
                  if not device.removed]
        #Wait parameters
        if wait:
            logger.info('Waiting for all devices to be '\
                        'removed from the beampath %s ...', self)
            #Wait consecutively for statuses, this can be done by combining
            #statuses in the future
            for s in status:
                logger.debug('Waiting for %s to be done ...', s)
                status_wait(s, timeout=timeout)
                logger.info('Completed')

        return status

    def join(self, *beampaths):
        """
        Join multiple beampaths with the current one

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
        return BeamPath.from_join(self, *beampaths, name=self.name)

    def split(self, z=None, device=None):
        """
        Split the beampath producing two new BeamPath objects either by a
        specific position or a devices location

        Parameters
        ----------
        z : float
            Z position to split the paths

        device  : LightDevice, name, or base PV
            The specified device will be the last device in the first
            :class:`.BeamPath` object

        Returns
        -------
        BeamPath, BeamPath
            Two new beampath instances
        """
        #Not enough information
        if not z and not device:
            raise ValueError("Must supply information where to split the path")
        #Grab the z if given a device
        if device:
            z = device.z
        #Look within range
        if z<self.range[0] or z>self.range[1]:
            raise ValueError("Split position {} is not within the range of "
                             "the path.".format(z))
        #Split the paths
        return (BeamPath(*[d for d in self.devices if d.z <= z]),
                BeamPath(*[d for d in self.devices if d.z >  z])
               )

    @classmethod
    def from_join(cls, *beampaths, name=None):
        """
        Join other beampaths with the current one

        Parameters
        ----------
        beampaths : arguments
            A list of beampaths to join into a complete path, order is
            irrelavant

        name : str, optional
            New name for created beampath

        Returns
        -------
        BeamPath : :class:`.BeamPath`
            A new object with all of the path devices

        Raises
        ------
        TypeError:
            Raised if a non-BeamPath object is supplied
        """
        #Catch invalid paths
        if not all(isinstance(bp,BeamPath) for bp in beampaths):
            raise TypeError('Can not join non-BeamPath object')
        #Flatten path lists
        devices = [device for path in beampaths for device in path.devices]
        #Create a new instance
        return BeamPath(*set(devices), name=name)

    def _ignore(self, ignore_devices, passive=False):
        """
        Assemble list of available devices with some exclusions

        Parameters
        ----------
        ignore_devices : list
            Devices to ignore

        passive : bool
            If False, ignore passive devices

        Returns
        -------
        (target, ignore) : tuple
            Tuple of two lists of devices
        """
        ignore = list()

        #Add passive devices to ignored
        if not passive:
            logger.debug("Passive devices will be ignored ...")
            ignore.extend([d for d in self.devices
                           if d.transmission > self.minimum_transmission])
        #Add ignored devices
        if isinstance(ignore_devices, Iterable):
            ignore.extend(ignore_devices)
        elif ignore_devices:
            ignore.append(ignore_devices)
        #Grab target devices
        target_devices = [device for device in self.devices
                          if device not in ignore]
        logger.debug("Targeting devices %s ...", target_devices)
        logger.debug('Ignoring devices %s ...', ignore)
        return target_devices, ignore

    def _device_moved(self, *args, obj=None, **kwargs):
        """
        Run when a device changes state
        """
        #Maybe this should introspect and see if beampath state changes
        self._run_subs(sub_type = self.SUB_PTH_CHNG,
                         device = obj)
        #Alert that an MPS system has moved
        if getattr(obj, 'mps', None):
            self._run_subs(sub_type=self.SUB_MPSPATH_CHNG,
                          device=obj)

    def _repr_info(self):
        yield('range',   self.range)
        yield('devices', len(self.devices))

    __hash = object.__hash__

    def __eq__(self, *args, **kwargs):
        try:
            return self.devices == args[0].devices
        except AttributeError:
            return super().__eq__(*args, **kwargs)
