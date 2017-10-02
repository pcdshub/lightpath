"""
While the :class:`.BeamPath` object provides basic control functionality, the
:class:`.LightController` is what does the organization of all of LCLS's
devices. After parsing through all of the given devices, each beamline is
contsructed as a :class:`.BeamPath` object. This includes not only devices on
the upstream beamline but all of the beamlines before it. For example, the MEC
beampath will include devices in both the FEE and the XRT. The
:class:`.LightController` handles this logic as well as a basic overview of
where the beam is and what the state of the MPS system is currently. 
"""
####################
# Standard Library #
####################
import logging
####################
#    Third Party   #
####################

####################
#     Package      #
####################
from .path import BeamPath

logger = logging.getLogger(__name__)

class LightController:
    """
    Controller for the LCLS Lightpath

    Handles grouping devices into beamlines and joining paths together. Also
    provides an overview of the state of the entire beamline

    Parameters
    ----------
    args :
        LCLS Devices
    """

    def __init__(self, *devices):
        #Create segmented beampaths beamlines
        self.beamlines = dict((line, BeamPath(*[dev for dev in devices
                                                if dev.beamline == line],
                                                name=line))
                              for line in set(d.beamline for d in devices))

        #Iterate through creating complete paths 
        for bp in sorted(self.beamlines.values(),
                         key = lambda x : x.path[0].z):
            logger.debug("Assembling complete beamline %s ...", bp.name)

            #Grab branches off the beamline
            for branch in bp.branches:
                logger.info("Found branches onto beamlines %s from %s",
                             ', '.join(branch.branches), branch.name)
                for dest in branch.branches:
                    if dest != bp.name:
                        #If this is a branch that can pass beam through
                        #without renaming the beamline split
                        if branch.beamline in branch.branches: 
                            section, after = bp.split(device=branch)
                        else:
                            section = bp
                        #Join with downstream path
                        logger.debug("Joining %s and %s", bp.name, dest)
                        try:
                            self.beamlines[dest] = self.beamlines[dest].join(
                                                                        section)
                        except KeyError:
                            logger.critical("Device %s has invalid branching "
                                            "dest %s", branch.name, dest)
            #Set as attribute for easy access
            setattr(self, bp.name.replace(' ','_').lower(),
                    self.beamlines[bp.name])

    @property
    def destinations(self):
        """
        Current device destinations for the LCLS photon beam
        """
        return list(set([p.impediment for p in self.beamlines.values()
                         if p.impediment and p.impediment not in p.branches]))

    @property
    def tripped_devices(self):
        """
        List of all tripped MPS devices in LCLS
        """
        devices = list()

        for line in self.beamlines.values():
            devices.extend(line.tripped_devices)

        return list(set(devices))

    @property
    def devices(self):
        """
        All of the devices loaded into beampaths
        """
        devices = list()

        for line in self.beamlines.values():
            devices.extend(line.devices)

        return list(set(devices))

    @property
    def incident_devices(self):
        """
        List of all devices in contact with photons along the beamline
        """
        devices = list()

        for line in self.beamlines.values():
            devices.extend(line.incident_devices)

        return list(set(devices))

    def path_to(self, device):
        """
        Create a BeamPath from the source to the requested device

        Parameters
        ----------
        device : Device
            A device somewhere in LCLS

        Returns
        -------
        path : :class:`BeamPath`
            Path to and including given device
        """
        try:
            prior, after = self.beamlines[device.beamline].split(device=device)

        except KeyError:
            raise ValueError("Beamline {} not found".format(device.beamline))

        return prior
