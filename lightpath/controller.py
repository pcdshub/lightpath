"""
While the :class:`.BeamPath` object provides basic control functionality, the
:class:`.LightController` is what organizes of all of LCLS's
devices. The facility is represented by an Directed Graph, starting at the
source and ending at the beamline hutches.  After placing each device in the
facility graph, each beamline is constructed as a :class:`.BeamPath` object.

This includes not only devices on the upstream beamline but all of the
beamlines before it. For example, the MEC beampath will include devices in both
the FEE and the XRT.  The MEC beampath will also contain devices that appear in
XPP's and XCS's beampath. In some cases there are multiple possible paths beam
may take to reach a given endstation.  In the case of multiple possible paths,
the :meth:`.LightController.active_path` will return the path with the latest
impediment.  (equivalently, the path that lets the beam through farthest)

The :class:`.LightController` handles this logic as well as a basic overview of
where the beam is
"""
import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import networkx as nx
from happi import Client, SearchResult
from networkx.exception import NodeNotFound
from ophyd import Device

from .config import beamlines
from .config import sources as default_sources
from .errors import PathError
from .mock_devices import Crystal, Valve
from .path import BeamPath

logger = logging.getLogger(__name__)

NodeName = str
MaybeBeamPath = List[Union[List[NodeName], BeamPath]]


@dataclass
class NodeMetadata:
    res: Optional[SearchResult] = None
    dev: Optional[Device] = None


class LightController:
    """
    Controller for the LCLS Lightpath

    Handles grouping devices into beamlines and joining paths together. Also
    provides an overview of the state of the entire beamline

    Parameters
    ----------
    client : happi.Client
        Happi Client

    endstations: List[str], optional
        List of experimental endstations to load BeamPath objects for. If left
        as None, all endstations will be loaded
    """
    graph: nx.DiGraph

    def __init__(
        self,
        client: Client,
        endstations: Optional[List[str]] = None,
        cfg: Dict[str, Any] = {}
    ):
        self.client: Client = client
        config = {
            'beamlines': beamlines,
            'hutches': endstations,
            'sources': default_sources,
            'min_trans': 0.1
        }
        # update default config with provided cfg
        config.update(cfg)
        self.beamline_config = config['beamlines']
        self.hutches = config['hutches']
        self.default_sources = config['sources']
        self.min_trans = config['min_trans']

        # a mapping of endstation name to either a path or initialized BeamPath
        self.beamlines: Dict[str, MaybeBeamPath] = dict()
        # sources found in facility
        self.sources: Set[str] = set()

        # initialize graph -> self.graph
        self.load_facility()

        dests = (self.hutches or (self.beamline_config or {}).keys())
        # Find the requisite beamlines to reach our endstation
        for beamline in dests:
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
        if len(results) < 1:
            raise ValueError('No lightpath-active devices found')
        # gather devices by branch
        branch_dict = {}
        for res in results:
            for branch_set in (res.metadata.get('input_branches', []),
                               res.metadata.get('output_branches', [])):
                if branch_set is None:
                    raise ValueError(
                        f'device {res.item.name} has no branch information, '
                        'check to make sure your happi database is '
                        'correctly implementing its container.')
                for branch in branch_set:
                    branch_dict.setdefault(branch, set()).add(res)

        # Construct subgraphs and merge
        subgraphs = []
        for branch_name, branch_devs in branch_dict.items():
            subgraph = self.make_graph(
                branch_devs,
                sources=self.default_sources,
                branch_name=branch_name
            )
            self.sources.update((n for n in subgraph
                                 if self.is_source_name(n)))
            subgraphs.append(subgraph)

        self.graph = nx.compose_all(subgraphs)

    def load_beamline(self, endstation: str):
        """
        Load a beamline given the facility graph.  Finds all possible
        paths from facility sources to the endstation's branch.
        Branches are mapped to endstations in the config.
        Each branch can be optionally mapped to a final z to
        consider part of the path.

        Loads valid beampaths into the LightController.beamlines
        attribute for latedr access.

        Parameters
        ----------
        endstation : str
            Name of endstation to load
        """
        try:
            end_branches = self.beamline_config[endstation]
        except KeyError:
            logger.warning("Unable to find %s as a configured endstation, "
                           "assuming this is an invalid path", endstation)
            return

        paths = list()
        for branch in end_branches:
            # Find the paths from each source to the desired line
            for src in self.sources:
                try:
                    if nx.has_path(self.graph, src, branch):
                        found_paths = nx.all_simple_paths(self.graph,
                                                          source=src,
                                                          target=branch)
                        paths.extend(found_paths)
                    else:
                        logger.debug(f'No path between {src} and {branch}')
                except NodeNotFound:
                    logger.debug(f'Either source {src} or target {branch} '
                                 'not found.')

        self.beamlines[endstation] = paths

    def get_paths(self, endstation: str) -> List[BeamPath]:
        """
        Returns the BeamPaths for a specified endstation.
        Create and fill the BeamPaths if they have not been already

        Parameters
        ----------
        endstation : str
            name of endstation to return paths for

        Returns
        -------
        List[BeamPath]
            a list of BeamPath's to the requested endstation
        """
        # if path exists, return it
        paths = self.beamlines[endstation]

        if all([isinstance(path, BeamPath) for path in paths]):
            return paths

        # create the BeamPaths if they have not been already
        end_branches = self.beamline_config[endstation]
        filled_paths = []
        for path in paths:
            subgraph = self.graph.subgraph(path)
            devices = [self.get_device(dev_name)
                       for dev_name, data in subgraph.nodes.data()
                       if data['md'].res is not None]
            bp = BeamPath(
                *devices,
                name=endstation,
                minimum_transmission=self.min_trans
            )

            if isinstance(end_branches, dict):
                # access the last z for this branch
                # if end_branches is Dict[BranchName, end_z], grab last
                # allowable z with the branch name (last node in path)
                last_z = end_branches[path[-1]]
                if last_z:
                    # append path with all devices before last z
                    filled_paths.append(bp.split(last_z)[0])
                else:
                    filled_paths.append(bp)
            elif isinstance(end_branches, list):
                # end_branches is a simple list, no splitting needed
                filled_paths.append(bp)
            else:
                raise TypeError('config is incorrectly formatted '
                                f'(found mapping from {endstation} to '
                                f'{type(end_branches)}).')

        self.beamlines[endstation] = filled_paths
        return filled_paths

    @staticmethod
    def imped_z(path: BeamPath) -> float:
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
        paths = self.get_paths(dest)
        if len(paths) == 0:
            raise PathError('No paths in facility to the '
                            f'desired endstation: {dest}')
        if len(paths) == 1:
            return paths[0]

        paths_by_length = sorted(paths, key=self.imped_z)

        return paths_by_length[-1]

    @staticmethod
    def is_source_name(name: str) -> bool:
        """
        Checks if the node name provided is a valid source name

        Parameters
        ----------
        name : str
            name to check

        Returns
        -------
        bool
            if name is a valid source name
        """
        return name.startswith('source_')

    def walk_facility(self) -> Dict[NodeName, List[NodeName]]:
        """
        Return the paths from each source to its destination by walking the
        graph.

        Starting from a source node, steps iteratively through a node's
        successors (nearest neighbors).  If there is one and only one valid
        successor, step to that device and repeat.  Once there are no more
        connections, we have reached the end of the line.

        Successors are considered invalid if a node's output branch does not
        match the successor's input.

        Returns
        -------
        Dict[NodeName, List[NodeName]]
            A mapping from source node names to path of nodes

        Raises
        ------
        PathError
            If a single, valid path cannot be determined
        """
        paths: Dict[NodeName, List] = {k: [] for k in self.sources}

        for src, path in paths.items():
            successors = list(self.graph.successors(src))
            # skip to node after source node
            try:
                curr = successors[0]
            except IndexError:
                raise PathError(f'Isolated node ({src}) in graph, has '
                                'no successors.  Database may be '
                                'misconfigured')
            curr_dev = self.get_device(curr)

            while successors:
                # get output branches that receive beam
                out_branches = get_active_outputs(curr_dev)
                connections = []
                for succ in successors:
                    succ_dev = self.get_device(succ)
                    if succ_dev is None:
                        # reached a node without a device, (the end)
                        continue

                    in_branches = succ_dev.input_branches

                    active_links = [b for b in out_branches
                                    if b in in_branches]
                    if active_links:
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
                curr_dev = self.get_device(curr)
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
        def find_dest(path):
            """ small closure to cache the impediment"""
            imped = path.impediment
            if imped is not None and imped not in path.branching_devices:
                return imped

        dests = set()
        for endstation in self.beamlines.keys():
            paths = self.get_paths(endstation)
            for path in paths:
                dest = find_dest(path)
                if dest is not None:
                    dests.add(dest)

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
        return [n[1]['md'].dev for n in self.graph.nodes.data()]

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

        for endstation in self.beamlines.keys():
            paths = self.get_paths(endstation)
            for path in paths:
                devices.update(path.incident_devices)

        return list(devices)

    def paths_to(self, device: Device) -> List[BeamPath]:
        """
        Create all BeamPaths from the facility source to the requested device

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
        paths : List[:class:`BeamPath`]
            Paths to and including given device
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
            devs = [data['md'].dev for _, data in subg.nodes.data()
                    if data['md'].dev is not None]
            beampaths.append(
                BeamPath(
                    *devs,
                    name=f'{device.md.name}_path',
                    minimum_transmission=self.min_trans
                )
            )

        return beampaths

    def path_to(self, device: Device) -> BeamPath:
        """
        Returns the path with latest blocking device
        (highest blocking z-position) to the requested device

        To get all possible paths, see ``LightController.paths_to``

        Parameters
        ----------
        device : Device
            A device somewhere in the facility

        Returns
        -------
        BeamPath
            path to the specified device
        """
        return sorted(self.paths_to(device), key=self.imped_z)[-1]

    @staticmethod
    def make_graph(
        branch_devs: List[SearchResult],
        branch_name: str,
        sources: List[NodeName] = []
    ) -> nx.DiGraph:
        """
        Create a graph with devices from ``branch_devs`` as nodes,
        arranged in z-order.

        It is assumed that all devices lie on branch: ``branch_name``

        If ``sources`` is provided, will prepend a source node at the
        beginning of the branch if ``branch_name == sources``

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
        # label nodes with device name, store SearchResult and leave
        # a place for the ophyd device
        nodes = []
        for res in result_list:
            nodes.append((res.metadata['name'],
                         {'md': NodeMetadata(res=res, dev=None)}))

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
            curr_dev = nodes[i][1]['md'].res
            if (branch_name in curr_dev.metadata['input_branches'] and
                    branch_name in curr_dev.metadata['output_branches']):
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
                next_dev = nodes[i+1][1]['md'].res
            except IndexError:
                # we are at the end, skip steps that look ahead
                continue

            if (set(curr_dev.metadata['output_branches']) &
                    set(next_dev.metadata['input_branches'])):
                # base case, make edge as normal
                edges.append((nodes[i][0], nodes[i+1][0], edata))
            # process dangling nodes.  Here we skip making edges for
            # this node, and attach it to next node with branch_name
            # as its input and output (saved as last_on_branch)
            elif (branch_name not in curr_dev.metadata['input_branches']):
                skipped_left.append(i)
            elif (branch_name not in curr_dev.metadata['output_branches']):
                skipped_right.append(i)

        # add sources
        if branch_name in sources:
            nodes.insert(0, (f'source_{branch_name}',
                             {'md': NodeMetadata()}))
            edges.append((nodes[0][0], nodes[1][0], edata))
        # add end point
        nodes.append((branch_name, {'md': NodeMetadata()}))
        edges.append((nodes[-2][0], nodes[-1][0], edata))

        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)

        graph.name = str(branch_name)
        return graph

    def get_device(self, device_name: NodeName) -> Device:
        """
        Return device in the facility.  Creates the device if it has
        not been already.

        Parameters
        ----------
        device : NodeName
            name of device

        Returns
        -------
        Device
            requested device, or a mock version of the device
        """
        try:
            dev_data = self.graph.nodes[device_name]['md']
        except KeyError:
            logger.error(f'requested device ({device_name}) not in facility')
            return

        if dev_data.dev is not None:
            return dev_data.dev
        elif dev_data.res is not None:
            # not instantiated yet, create and fill
            try:
                dev = dev_data.res.get()
                self.graph.nodes[device_name]['md'].dev = dev
                return dev
            except Exception:
                logger.error(f'Device {device_name} failed to load, '
                             'attempting to make a mock device')
                dev = make_mock_device(dev_data.res)
                self.graph.nodes[device_name]['md'].dev = dev
                return dev


def get_active_outputs(device: Device) -> List[str]:
    """
    Returns a list of branch names that are receiving beam.
    Alternatively, returns a list of branches this device is delivering
    beam to with transmission > 0.

    Parameters
    ----------
    device : Device
        Device to get active output branches for

    Returns
    -------
    List[str]
        List of active branches
    """
    outputs = device.get_lightpath_state().output

    return [br for br, trans in outputs.items() if trans > 0]


def make_mock_device(result: SearchResult) -> Device:
    """
    Create a mock device that implements the Lightpath Interface using
    the metadata provided. If more than one output branch is found,
    uses a slightly more complicated ``Crystal`` mock device.  Creates
    a ``Valve`` mock device otherwise

    Parameters
    ----------
    result : SearchResult
        a happi.SearchResult containing the metadata needed to mock

    Returns
    -------
    Device
        a mock device usable in the Lightpath app
    """
    md = result.metadata
    if len(md['output_branches']) > 1:
        MockClass = Crystal
    else:
        MockClass = Valve

    mock_dev = MockClass(md['prefix'], name='MOCK_' + md['name'], z=md['z'],
                         input_branches=md['input_branches'],
                         output_branches=md['output_branches'])

    return mock_dev
