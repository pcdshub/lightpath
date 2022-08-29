142 fix_gui_tests
#################

API Changes
-----------
- N/A

Features
--------
- Add the option to specify an end-z in the beamlines config, for endstations that exist in the middle of a branch.

Bugfixes
--------
- Fixes behavior of upstream filter checkbox by converting it to a combo box that allows users to select a device to filter devices upstream of.  This now works with the current facility representation.
- Disables happi caching to prevent devices from persisting across tests.
- Extends the default EpicsSignal timeout to allow devices to connect.

Maintenance
-----------
- GUI now subscribes to lightpath_summary signals instead of the device
- Remove unneeded call to ``lightpath_summary.get``
- Properly unsubscribes from signals on GUI shutdown

Contributors
------------
- tangkong
