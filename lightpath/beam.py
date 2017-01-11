import logging
from   psp import PV


class Beam(object):
    """
    Class to hold statistics about the beam
    """
    def __init__(self):
        self._transmission = 1.0

    @property
    def transmission(self):
        """
        Current transmisison ratio of the beam
        """
        return self._transmission


    @propety
    def is_produced(self):
        """
        Whether beam is being produced at the beginning of the FEE
        """
        return 


    @property
    def energy
        """
        Current reporeted energy of the XFEL
        """
        return 


    @property
    def repetition_rate


    def attenuate


    def __copy__
