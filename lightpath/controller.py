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
            logger.debug("Assembling complete beamline {} ...".format(bp.name))

            #Grab branches off the beamline
            for branch in bp.branches:
                logger.info("Found branches onto beamlines {} from {} "
                             "".format(', '.join(branch.branches),
                                       branch.name))
                for destination in branch.branches:
                    if destination != bp.name:
                        try:
                            #Split path up before branching device
                            prior, after = bp.split(device=branch)
                            #Join with downstream path
                            logger.debug("Joining {} and {}".format(bp.name,
                                                                    destination))
                            self.beamlines[destination] = self.beamlines[destination].join(prior)

                        except KeyError:
                            logger.critical("Device {} has invalid branching "
                                            "destination {}".format(branch.name,
                                                                    destination))
            #Set as attribute for easy access
            setattr(self, bp.name.replace(' ','_').lower(),
                    self.beamlines[bp.name])


    @property
    def destinations(self):
        """
        Current beam ending points
        """
        return list(set([p.impediment for p in self.beamlines.values()
                         if p.impediment and p.impediment not in p.branches]))


    @property
    def tripped_devices(self):
        """
        List of all tripped MPS devices along the beamline
        """
        devices = list()

        for line in self.beamlines.values():
            devices.extend(line.tripped_devices)

        return list(set(devices))


    @property
    def devices(self):
        """
        All LCLS Devices
        """
        devices = list()

        for line in self.beamlines.values():
            devices.extend(line.devices)

        return list(set(devices))


    @property
    def incident_devices(self):
        """
        List of all faulted devices along the beamline
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
        """
        try:
            prior, after = self.beamlines[device.beamline].split(device=device)

        except KeyError:
            raise ValueError("Beamline {} not found".format(device.beamline))

        return prior
