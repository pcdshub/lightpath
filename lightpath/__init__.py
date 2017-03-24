__all__ = ['device']

import logging

from .path       import BeamPath
from .device     import LightDevice
from .utils      import MPS
from .controller import LightController

#Setup logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.CRITICAL)

#For development
def DEBUG():
    logger.setLevel(logging.DEBUG)

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
