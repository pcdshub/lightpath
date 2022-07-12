133 enh_graphs_interface
########################

API Changes
-----------
- switches assumed device interface to expect a single get_lightpath_state function, which returns a LightpathState dataclass
- removes SUB_STATE in favor of subscribing to a single ``lightpath_summary`` signal, which aggregates relevant device signals
- A short summary of added methods
  - ``BeamPath``: adds ``load_facility``, ``walk_facility``, ``make_graph``
  - ``LightController``: renames ``branches`` to ``branching_devices``

Features
--------
- represents the facility as a directed graph, with devices as nodes
- uses path-finding algorithms to find routes to beamlines
- adds methods to handle multiple possible paths to a single destination

Bugfixes
--------
- N/A

Maintenance
-----------
- adds pre-release note framework
- updates tests to test new API
- updates test database to more accurately simulate LCLS facility complexity
- updates docs
- adds type hinting throughout

Contributors
------------
- tangkong
