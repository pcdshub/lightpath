188 mnt_malformed_device_handling
#################################

API Changes
-----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- N/A

Maintenance
-----------
- Remove hard failure when a lightpath-active device is malformed.  Instead of throwing an
  exception, simply omit it from the facility graph
- Trim beam paths before BeamPath objects are created, when device names are gathered into paths

Contributors
------------
- tangkong
