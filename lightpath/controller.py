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
import logging
import math

import networkx as nx

from .config import beamlines, sources
from .path import BeamPath

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
        self.graph = nx.DiGraph()
        self.sources = set()

        # initialize graph -> self.graph
        self.load_facility()

        endstations = endstations or beamlines.keys()
        # # Find the requisite beamlines to reach our endstation
        for beamline in endstations:
            self.load_beamline(beamline)

    def load_facility(self):
        """
        Load the facility from the provided happi client.

        The facility is represented by a directed graph, with
        SearchResults as nodes.
        """
        results = self.client.search_range(key='z', start=0.0, end=math.inf,
                                           active=True, lightpath=True)
        # gather devices by branch
        branch_dict = {}
        for res in results:
            for branch_set in (res.metadata.get('input_branches', []),
                               res.metadata.get('output_branches', [])):
                for branch in branch_set:
                    if branch not in branch_dict:
                        branch_dict[branch] = set()
                    branch_dict[branch].add(res)

        # Construct subgraphs and merge
        subgraphs = []
        for branch_name, branch_devs in branch_dict.items():
            subgraph = BeamPath.make_graph(branch_devs,
                                           sources=sources,
                                           branch_name=branch_name)
            self.sources.update((n for n in subgraph if 'source' in n))
            subgraphs.append(subgraph)

        self.graph = nx.compose_all(subgraphs)

    def load_beamline(self, endstation):
        """
        Load a beamline given the facility graph.  Find path from source
        to endstation with reasonable transmission

        Parameters
        ----------
        endstation : str
            Name of endstation to load

        Returns
        -------
        path: BeamPath
        """
        try:
            end_branches = beamlines[endstation]
        except KeyError:
            logger.warning("Unable to find %s as a configured endstation, "
                           "assuming this is an independent path", endstation)
            # TODO: Look at all branches?  What to do here
            return

        paths = list()
        for branch in end_branches:
            # Find the paths from each source to the desired line
            for src in self.sources:
                if nx.has_path(self.graph, src, branch):
                    found_paths = nx.all_simple_paths(self.graph, source=src,
                                                      target=branch)
                    paths.extend(found_paths)
                else:
                    logger.debug(f'No path between {src} and {branch}')

        self.beamlines[endstation] = []
        for path in paths:
            subgraph = self.graph.subgraph(path)
            devices = [node[1]['dev'] for node in subgraph.nodes.data()
                       if node[1]['dev'] is not None]
            bp = BeamPath(*devices, name=endstation)
            self.beamlines[endstation].append(bp)

        setattr(self, bp.name.replace(' ', '_').lower(),
                self.beamlines[endstation])

    def active_path(self, endstation):
        """
        Return the most active path to the requested endstation

        Looks for the path with the latest impediment (highest z)
        """
        paths = self.beamlines[endstation]
        if len(paths) == 1:
            return paths[0]

        # sort paths by latest impediment z-position
        def imped_z(path):
            return getattr(path.impediment, 'md.z', math.inf)

        paths_by_length = sorted(paths, key=imped_z)

        return paths_by_length[-1]

    @property
    def destinations(self):
        """
        Current device destinations for the LCLS photon beam
        """
        dests = set()
        for paths in self.beamlines.values():
            dests.update([p.impediment for p in paths
                          if p.impediment and p.impediment not in p.branches])

        return dests

    @property
    def devices(self):
        """
        All of the devices loaded into beampaths
        """
        devices = set()

        for paths in self.beamlines.values():
            for path in paths:
                devices.update(path.devices)

        return list(devices)

    @property
    def incident_devices(self):
        """
        List of all devices in contact with photons along the beamline
        """
        devices = set()

        for paths in self.beamlines.values():
            for path in paths:
                devices.update(path.incident_devices)

        return list(devices)

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
        paths = list()
        for src in self.sources:
            if nx.has_path(self.graph, src, device.name):
                found_paths = nx.all_simple_paths(self.graph, source=src,
                                                  target=device.name)
                paths.extend(found_paths)
            else:
                logger.debug(f'No path between {src} and {device.name}')
                return None

        if len(paths) > 1:
            logger.debug('found two paths to requested device')

        # TODO: Deal with picking the right path
        subgraph = self.graph.subgraph(paths[0])
        devices = [node[1]['dev'] for node in subgraph.nodes.data()
                   if node[1]['dev'] is not None]
        return BeamPath(*devices, name=f'{device.name}_path')
