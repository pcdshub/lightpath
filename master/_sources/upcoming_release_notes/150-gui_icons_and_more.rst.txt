150 gui_icons_and_more
######################

API Changes
-----------
- N/A

Features
--------
- sets title of window based on current path
- dynamically populates device_type filters with module names of devices currently in path
- adds cumulative transmission along path as a blocking criteria
- updates device icon color logic to consider both device and path state

Bugfixes
--------
- removes endstation sorting to allow lazy BeamPath loading
- fixes various font-awesome deprecation warnings

Maintenance
-----------
- make the simulated lcls facility import-able
- adds tests for cumulative transmission and updated icon coloring
- make test_show_devices use regex instead of hard-coded output

Contributors
------------
- tangkong
