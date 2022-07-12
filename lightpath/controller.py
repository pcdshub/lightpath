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
from typing import Any, Dict, List, Set, Tuple

import networkx as nx
from happi import Client, SearchResult
from ophyd import Device

from .config import beamlines, sources
from .errors import PathError
from .path import BeamPath

logger = logging.getLogger(__name__)

NodeName = str


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
    graph: nx.DiGraph

    def __init__(self, client, endstations=None):
        self.client: Client = client
        self.beamlines: Dict[str, List[BeamPath]] = dict()
        self.sources: Set[str] = set()

        # initialize graph -> self.graph
        self.load_facility()

        endstations = endstations or beamlines.keys()
        # Find the requisite beamlines to reach our endstation
        for beamline in endstations:
            self.load_beamline(beamline)

    def load_facility(self):
        """
        Load the facility from the provided happi client.

        The facility is represented by a directed graph, with
        devices as nodes.  Edge weights are initialized as 0, and
        labeled with their branch.

        The facility graph is created by combining subgraphs that
        each contain all the devices on a given branch.
        """
        results = self.client.search_range(key='z', start=0.0, end=math.inf,
                                           active=True, lightpath=True)
        # gather devices by branch
        branch_dict = {}
        for res in results:
            for branch_set in (res.metadata.get('input_branches', []),
                               res.metadata.get('output_branches', [])):
                for branch in branch_set:
                    branch_dict.setdefault(branch, set()).add(res)

        # Construct subgraphs and merge
        subgraphs = []
        for branch_name, branch_devs in branch_dict.items():
            subgraph = LightController.make_graph(branch_devs,
                                                  sources=sources,
                                                  branch_name=branch_name)
            self.sources.update((n for n in subgraph if 'source' in n))
            subgraphs.append(subgraph)

        self.graph = nx.compose_all(subgraphs)

    def load_beamline(self, endstation: str):
        """
        Load a beamline given the facility graph.  Finds all possible
        paths from facility sources to the endstation's branch.
        Branches are mapped to endstations in the config

        Loads valid beampaths into the LightController.beamlines
        attribute for latedr access.

        Parameters
        ----------
        endstation : str
            Name of endstation to load
        """
        try:
            end_branches = beamlines[endstation]
        except KeyError:
            logger.warning("Unable to find %s as a configured endstation, "
                           "assuming this is an invalid path", endstation)
            return

        paths = list()
        for branch in end_branches:
            # Find the paths from each source to the desired line
            for src in self.sources:
                if nx.has_path(self.graph, src, branch):
                    found_paths = nx.all_simple_paths(self.graph,
                                                      source=src,
                                                      target=branch)
                    paths.extend(found_paths)
                else:
                    logger.debug(f'No path between {src} and {branch}')

        self.beamlines[endstation] = []
        for path in paths:
            subgraph = self.graph.subgraph(path)
            devices = [dat['dev'] for _, dat in subgraph.nodes.data()
                       if dat['dev'] is not None]
            bp = BeamPath(*devices, name=endstation)
            self.beamlines[endstation].append(bp)

        # This isn't used currently, but left for now
        setattr(self, bp.name.replace(' ', '_').lower(),
                self.beamlines[endstation])

    def imped_z(self, path: BeamPath) -> float:
        """
        Get z position of impediment or inf.

        Parameters
        ----------
        path : :class:`BeamPath`
            BeamPath to find impediment position in

        Returns
        -------
        float
            z position of impediment
        """
        return getattr(path.impediment, 'md.z', math.inf)

    def active_path(self, dest: str) -> BeamPath:
        """
        Return the most active path to the requested endstation

        Looks for the path with the latest impediment (highest z)

        Parameters
        ----------
        dest : str
            endstation to look for paths towards

        Returns
        -------
        path : :class:`BeamPath`
            the active path
        """
        paths = self.beamlines[dest]
        if len(paths) == 1:
            return paths[0]

        paths_by_length = sorted(paths, key=self.imped_z)

        return paths_by_length[-1]

    def walk_facility(self) -> Dict[NodeName, List[NodeName]]:
        """
        Return the paths from source to destination by walking the
        graph along device destinations

        Starting from a source node, steps iteratively through a node's
        successors (nearest neighbors).  If there is one and only one
        successor, step to that device and repeat.  Once there are no
        more connections, we have reached the end of the line and may stop.

        Successors are considered invalid if a node's output branch
        does not match the successor's input.

        Returns
        -------
        Dict[NodeName, List[NodeName]]
            A mapping from source node names to path of nodes

        Raises
        ------
        PathError
            If a single, valid path cannot be determined
        """
        sources = [n for n in self.graph.nodes if 'source' in n]

        paths: Dict[NodeName, List] = {k: [] for k in sources}

        for src, path in paths.items():
            successors = list(self.graph.successors(src))
            # skip to node after source node
            curr = successors[0]
            while successors:
                curr_dev = self.graph.nodes[curr]['dev']
                out_branch = curr_dev.get_lightpath_state().output_branch
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
    def destinations(self) -> List[Device]:
        """
        Current device destinations for the LCLS photon beam

        Returns
        -------
        List[Device]
            a list of beam destinations
        """
        dests = set()
        for paths in self.beamlines.values():
            dests.update([p.impediment for p in paths
                          if p.impediment and p.impediment
                          not in p.branching_devices])

        return list(dests)

    @property
    def devices(self) -> List[Device]:
        """
        All of the devices loaded in the facility

        Returns
        -------
        List[Device]
            list of devices loaded in the facility
        """
        return [n[1]['dev'] for n in self.graph.nodes.data()]

    @property
    def incident_devices(self) -> List[Device]:
        """
        List of all devices in contact with photons along the beamline

        Returns
        -------
        List[Device]
            list of all incident devices in facility
        """
        devices = set()

        for paths in self.beamlines.values():
            for path in paths:
                devices.update(path.incident_devices)

        return list(devices)

    def path_to(self, device: Device) -> BeamPath:
        """
        Create a BeamPath from the facility source to the requested device
        In the case of multiple valid paths, returns the path with latest
        blocking device (highest blocking z-position)

        Parameters
        ----------
        device : Device
            A device somewhere in LCLS

        Raises
        ------
        PathError
            If a single, valid path cannot be determined

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
            raise PathError(f'No paths from sources to {device.md.name}')

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
        branch_devs: List[SearchResult],
        branch_name: str,
        sources: List[NodeName] = []
    ) -> nx.DiGraph:
        """
        Create a graph with devices from branch_devs as nodes,
        arranged in z-order.

        It is assumed that all devices lie on branch: branch_name

        If sources is provided, will prepend a source node at the
        beginning of the branch when branch_name == sources

        Parameters
        ----------
        branch_devs : List[happi.SearchResult]
            a list of devices to generate graph with

        branch_name : str
            branch name, used to label edges

        sources : List[NodeName], optional
            source node Names, by default []

        Returns
        -------
        nx.DiGraph
            The branch comprised of nodes holding devices from branch_devs
        """
        graph = nx.DiGraph()
        result_list = list(branch_devs)
        result_list.sort(key=lambda x: x.metadata['z'])
        # label nodes with device name, store ophyd device
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
        edges: List[Tuple[NodeName, NodeName, Dict[str, Any]]] = []
        skipped_right: List[int] = []
        skipped_left: List[int] = []
        last_on_branch = 0
        # weight not used currently, but may be for path finding algos
        edata = {'weight': 0.0, 'branch': branch_name}
        # Need to properly handle "dangling" devices that either:
        # only have the current branch in their input (skipped_right)
        # - these devices will not have output edge
        # only have the current branch in their output (skipped_left)
        # - these devices will not have an input edge

        # These dangling nodes are distinct from branching nodes, and
        # will be joined when subgraphs are merged.

        # In addition, after dangling nodes are attached, non-dangling
        # nodes should be connected, skipping the dangling nodes.
        # Thus the last_on_branch device must be tracked
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

                    # make edge between last_on_branch and current node
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
            # process dangling nodes.  Here we skip making edges for
            # this node, and attach it to next node with branch_name
            # as its input and output (saved as last_on_branch)
            elif (branch_name not in curr_dev.input_branches):
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

    def get_device(self, device: NodeName) -> Device:
        """
        Return device from graph

        Parameters
        ----------
        device : NodeName
            name of device

        Returns
        -------
        Device
            requested device
        """
        try:
            return self.graph.nodes[device]['dev']
        except KeyError:
            logger.error(f'requested device ({device}) not found')
