Release History
###############


v1.0.2 (2023-04-04)
===================

Bugfixes
--------
- Prevents cli entrypoint from returning the LightApp instance.
- Filters the visible LightRow widgets after a path change.
  This fixes a bug where changing paths would show all devices on a path,
  ignoring the state of show-removed or device filter checkboxes.

Maintenance
-----------
- Removes pcdsdevices dependency by vendoring AggregateSignal.
- Copies test requirements into the conda recipe.
- Fix a pre-commit issue where we point to a defunct mirror of flake8.

Contributors
------------
- tangkong
- zllentz


v1.0.1 (2022-10-25)
===================

Bugfixes
--------
- ``LightController.load_beamlines`` now properly references the provided
  configuration if provided, rather than the default ``beamlines`` config

Contributors
------------
- tangkong


v1.0.0 (2022-09-28)
===================

API Changes
-----------
- Switches assumed device interface to expect a single get_lightpath_state
  function, which returns a LightpathState dataclass
- Removes SUB_STATE in favor of subscribing to a single ``lightpath_summary``
  signal, which aggregates relevant device signals
- A short summary of added methods

  - ``BeamPath``: adds ``load_facility``, ``walk_facility``, ``make_graph``
  - ``LightController``: renames ``branches`` to ``branching_devices``

Features
--------
- Adds support for multiple, simultaneous outputs on a device
- ``BeamPath`` now sorts devices at init and saves them in an OrderedDict
  for easy lookup of next device
- Adds lodcm mock classes for testing
- Add the option to specify an end-z in the beamlines config, for endstations
  that exist in the middle of a branch.
- Adds ability to start lightpath with a config file
- Checks for signal connection status before get_lightpath_state, preventing
  lengthy timeouts
- Adds a refresh button and loading splash screen
- Represents the facility as a directed graph, with devices as nodes
- Uses path-finding algorithms to find routes to beamlines
- Adds methods to handle multiple possible paths to a single destination
- Defers device instantiation until needed by BeamPath objects, loading
  facility graph with only happi database information
- Create a mock device if device in happi cannot be created
- Sets title of window based on current path
- Dynamically populates device_type filters with module names of devices
  currently in path
- Adds cumulative transmission along path as a blocking criteria
- Updates device icon color logic to consider both device and path state

Bugfixes
--------
- Fixes behavior of upstream filter checkbox by converting it to a combo
  box that allows users to select a device to filter devices upstream of
  This now works with the current facility representation
- Disables happi caching to prevent devices from persisting across tests
- Extends the default EpicsSignal timeout to allow devices to connect
- Prevent beamlines with no beampath from destination combo box
- Removes endstation sorting to allow lazy BeamPath loading
- Fixes various font-awesome deprecation warnings

Maintenance
-----------
- GUI now subscribes to lightpath_summary signals instead of the device
- Properly unsubscribes from signals on GUI shutdown
- Fixes some clipping issues with the device icons
- Reworks documentation to reflect recent changes to lightpath
- Removes hinted signal widgets loaded from typhos to reduce GUI load times
- Allows lightpath cli command to be run without arguments, loading all
  default hutches
- Adds pre-release note framework
- Updates tests to test new API
- Updates test database to more accurately simulate LCLS facility complexity
- Updates documentation with updated API and some tutorial information
- Adds type hinting throughout package
- Moves simulated out of the test suite for reuse elsewhere
- Make the simulated lcls facility import-able
- Adds tests for cumulative transmission and updated icon coloring
- Make ``test_show_devices`` use regex instead of hard-coded output

Contributors
------------
- tangkong
