160 enh_multi_output
####################

API Changes
-----------
- LightpathState combines transmission and output_branch into a single
  field called output, a mapping from output_branch to transmission on
  that branch

Features
--------
- adds support for multiple, simultaneous outputs on a device
- sorts devices at init and saves them in an OrderedDict for easy lookup
  of next device
- adds lodcm mock classes for testing

Bugfixes
--------
- N/A

Maintenance
-----------
- N/A

Contributors
------------
- tangkong
