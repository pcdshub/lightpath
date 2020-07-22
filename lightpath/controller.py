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
import math
import logging

from .path import BeamPath
from .config import beamlines

logger = logging.getLogger(__name__)


class LightController:
    """
    Controller for the LCLS Lightpath

    Handles grouping devices into beamlines and joining paths together. Also
    provides an overview of the state of the entire beamline

    Attributes
    ----------
    containers: list
        List of happi Device objects that were unable to be instantiated

    Parameters
    ----------
    client : happi.Client
        Happi Client

    endstations: list, optional
        List of experimental endstations to load BeamPath objects for. If left
        as None, all endstations will be loaded
    """
    def __init__(self, client, endstations=None):
        self.client = client
        self.containers = list()
        self.beamlines = dict()
        endstations = endstations or beamlines.keys()
        # Find the requisite beamlines to reach our endstation
        for beamline in endstations:
            self.load_beamline(beamline)

    def load_beamline(self, endstation):
        """
        Load a beamline from the provided happi client

        Parameters
        ----------
        endstation : str
            Name of endstation to load

        Returns
        -------
        path: BeamPath
        """
        try:
            path = beamlines[endstation]
            path[endstation] = dict()
        except KeyError:
            logger.warning("Unable to find %s as a configured endstation, "
                           "assuming this is an independent path", endstation)
            path = {endstation: {}}

        # Load the devices specified in the configuration
        devices = list()

        for line, info in path.items():
            # Find the happi containers for this section of beamlines
            start = info.get('start', 0.0)
            end = info.get('end', math.inf)
            logger.debug("Searching for devices on line %s between %s and %s",
                         line, start, end)
            results = self.client.search_range(key='z', start=start, end=end,
                                               beamline=line, active=True,
                                               lightpath=True)
            # Ensure we actually found valid devices
            if not results:
                logger.error("No valid beamline devices found for %s", line)
                continue
            # Load all the devices we found
            logger.debug("Found %s devices along %s", len(results), line)
            for result in results:
                try:
                    dev = result.get()
                    devices.append(dev)
                except Exception:
                    logger.exception("Failure loading %s ...", result["name"])
                    self.containers.append(result.device)
        # Create the beamline from the loaded devices
        bp = BeamPath(*devices, name=line)
        self.beamlines[line] = bp
        # Set as attribute for easy access
        setattr(self, bp.name.replace(' ', '_').lower(), bp)
        return bp

    @property
    def destinations(self):
        """
        Current device destinations for the LCLS photon beam
        """
        return list(set([p.impediment for p in self.beamlines.values()
                         if p.impediment and p.impediment not in p.branches]))

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
            bl = self.beamlines[device.md.beamline]
            prior, after = bl.split(device=device)

        except KeyError:
            raise ValueError("Beamline {} not found".format(bl.name))

        return prior
