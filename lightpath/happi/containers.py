"""
Define subclasses of Happi Items for use with Lightpath
"""
import re
from copy import deepcopy

from happi.item import EntryInfo, OphydItem


class LightpathItem(OphydItem):
    name = EntryInfo(('Shorthand Python-valid name for the Python instance. '
                      'Must be between 3 and 80 characters.'),
                     optional=False,
                     enforce=re.compile(r'[a-z][a-z\_0-9]{2,78}$'))
    kwargs = deepcopy(OphydItem.kwargs)
    kwargs.default = {'name': '{{name}}',
                      'input_branches': '{{input_branches}}',
                      'output_branches': '{{output_branches}}',
                      }
    z = EntryInfo('Beamline position of the device',
                  enforce=float, default=-1.0)
    lightpath = EntryInfo("If the device should be included in the "
                          "LCLS Lightpath", enforce=bool, default=False,
                          optional=False)
    active = EntryInfo("If the device is currently active",
                       optional=False, enforce=bool, default=False)
    input_branches = EntryInfo(('List of branches the device can receive '
                                'beam from.'),
                               optional=False, enforce=list)
    output_branches = EntryInfo(('List of branches the device can deliver '
                                'beam to.'),
                                optional=False, enforce=list)
