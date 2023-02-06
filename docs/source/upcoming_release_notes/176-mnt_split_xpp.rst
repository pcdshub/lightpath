176 mnt_split_xpp
#################

API Changes
-----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- filters the visible LightRow widgets after a path change. This fixes a bug where changing paths would show all devices on a path, ignoring the state of show-removed or device filter checkboxes.

Maintenance
-----------
- Splits the XPP line into 'XPP_PINK' and 'XPP_MONO' so both are visible and selectable.  This change only affects the default config file; the ability to specify multiple paths or endpoints for a single name in the config remains.
- Copies test requirements into the conda recipe

Contributors
------------
- tangkong
