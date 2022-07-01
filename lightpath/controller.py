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
from typing import Any, List

import networkx as nx

from .config import beamlines, sources
from .errors import PathError
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
            subgraph = LightController.make_graph(branch_devs,
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

        # This isn't used currently, but left for now
        setattr(self, bp.name.replace(' ', '_').lower(),
                self.beamlines[endstation])

    def imped_z(self, path):
        """Get z position of impediment"""
        return getattr(path.impediment, 'md.z', math.inf)

    def active_path(self, dest):
        """
        Return the most active path to the requested endstation

        Looks for the path with the latest impediment (highest z)
        """
        paths = self.beamlines[dest]
        if len(paths) == 1:
            return paths[0]

        paths_by_length = sorted(paths, key=self.imped_z)

        return paths_by_length[-1]

    def walk_facility(self):
        """
        Return the path from source to destination by walking the
        graph along device destinations
        """

        sources = [n for n in self.graph.nodes if 'source' in n]

        paths = {k: [] for k in sources}

        for src, path in paths.items():
            successors = list(self.graph.successors(src))
            # skip to node after source node
            curr = successors[0]
            while successors:
                curr_dev = self.graph.nodes[curr]['dev']
                out_branch = curr_dev.get_lightpath_status().output_branch
                connections = []
                for succ in successors:
                    succ_dev = self.graph.nodes[succ]['dev']
                    if succ_dev is None:
                        # reached a node without a device, (the end)
                        break
                    in_branches = succ_dev.input_branches
                    if out_branch in in_branches:
                        connections.append(succ)

                if not connections:
                    # should be at the end
                    break
                elif len(connections) > 1:
                    raise PathError(
                        f'indeterminate pathing, {succ} has '
                        f'multiple valid children: {connections}'
                    )

                curr = connections[0]
                path.append(curr)
                curr_dev = self.graph.nodes[curr]['dev']
                successors = list(self.graph.successors(curr))

        return paths

    @property
    def destinations(self):
        """
        Current device destinations for the LCLS photon beam
        """
        dests = set()
        for paths in self.beamlines.values():
            dests.update([p.impediment for p in paths
                          if p.impediment and p.impediment not in p.branches])

        return list(dests)

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
            if nx.has_path(self.graph, src, device.md.name):
                found_paths = nx.all_simple_paths(self.graph, source=src,
                                                  target=device.md.name)
                paths.extend(found_paths)
            else:
                logger.debug(f'No path between {src} and {device.md.name}')

        if not paths:
            logger.debug(f'No paths found from sources to {device.md.name}')
            return None
        if len(paths) > 1:
            logger.debug('found two paths to requested device')

        subgraphs = [self.graph.subgraph(p) for p in paths]
        beampaths = []
        for subg in subgraphs:
            devs = [node[1]['dev'] for node in subg.nodes.data()
                    if node[1]['dev'] is not None]
            beampaths.append(BeamPath(*devs, name=f'{device.md.name}_path'))

        paths_by_length = sorted(beampaths, key=self.imped_z)

        return paths_by_length[-1]

    @staticmethod
    def make_graph(
        # happi.client.SearchResult, but entrypoints cause circular imports
        branch_devs: List[Any],
        branch_name: str,
        sources: List[str] = []
    ) -> nx.DiGraph:
        graph = nx.DiGraph()
        result_list = list(branch_devs)
        result_list.sort(key=lambda x: x.metadata['z'])
        # label nodes with device name, store device
        nodes = []
        for res in result_list:
            try:
                dev = res.get()
            except Exception:
                # TODO: be better about specific exceptions
                logger.debug(
                    f'Failed to initialize device: {res["name"]}'
                )
                continue
            nodes.append((res.metadata['name'], {'dev': dev}))

        # construct edges
        edges = []
        skipped_right = []
        skipped_left = []
        last_on_branch = 0
        edata = {'weight': 0.0, 'branch': branch_name}
        # Need to properly handle devices that either:
        # only have the current branch in their input (skipped_right)
        # only have the current branch in their output (skipped_left)
        for i in range(len(nodes)):
            curr_dev = nodes[i][1]['dev']
            if (branch_name in curr_dev.input_branches and
                    branch_name in curr_dev.output_branches):
                if last_on_branch != i:
                    # attach skipped devices
                    for ri in skipped_right:
                        edges.append((nodes[last_on_branch][0],
                                     nodes[ri][0], edata))
                    skipped_right = []

                    for li in skipped_left:
                        edges.append((nodes[li][0], nodes[i][0], edata))
                    skipped_left = []

                    # make edge between last on branch and this on dev
                    # luckily duplicate edges are ignored
                    edges.append((nodes[last_on_branch][0],
                                 nodes[i][0], edata))
                # update last_on_branch
                last_on_branch = i

            try:
                next_dev = nodes[i+1][1]['dev']
            except IndexError:
                # we are at the end, skip steps that look ahead
                continue

            if set(curr_dev.output_branches) & set(next_dev.input_branches):
                # base case, make edge as normal
                edges.append((nodes[i][0], nodes[i+1][0], edata))
            elif (branch_name not in curr_dev.input_branches):
                # skip this, attach it to next
                skipped_left.append(i)
            elif (branch_name not in curr_dev.output_branches):
                skipped_right.append(i)

        # add sources
        if branch_name in sources:
            nodes.insert(0, (f'source_{branch_name}', {'dev': None}))
            edges.append((nodes[0][0], nodes[1][0], edata))
        # add end point
        nodes.append((branch_name, {'dev': None}))
        edges.append((nodes[-2][0], nodes[-1][0], edata))

        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)

        graph.name = str(branch_name)
        return graph

    def get_device(self, key):
        """Return device from graph"""
        return self.graph.nodes[key]['dev']
