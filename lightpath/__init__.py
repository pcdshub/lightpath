__all__ = ['device']

import logging

from .path   import BeamPath
from .device import LightDevice

#Setup logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.CRITICAL)

#For development
def DEBUG():
    logger.setLevel(logging.DEBUG)
