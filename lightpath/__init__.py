__all__ = ['device']

import logging

from device import LightDevice, Component

#Setup logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.CRITICAL)

#For development
def DEBUG():
    logging.setLevel(logging.DEBUG)
