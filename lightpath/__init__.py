__all__ = ['device']

from . import _version
from .controller import LightController  # noqa
from .path import BeamPath  # noqa

__version__ = _version.get_versions()['version']
