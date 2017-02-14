import logging
from enum import Enum
from psp import PV


#class Frequency(Enum):
#    120Hz = 0
#    30Hz  = 1
#    10Hz  = 2
#    5Hz   = 3
#    1Hz   = 4
#    1_2Hz = 5 

class Beam(object):
    """
    Class to hold statistics about the beam
    """
    energy = C(EpicsSignalR0, 'SIOC:SYS0:ML00:A0627')
    beamrate = C(EpicsSignalR0, 'EVN:SYS0:1:LCLSBEAMRATE')

    def __init__(self):
        self._transmission = 1.0

    @property
    def transmission(self):
        """
        Current transmisison ratio of the beam
        """
        return self._transmission


#    @propety
#    def is_produced(self):
#        """
#        Whether beam is being produced at the beginning of the FEE
#        """
#        return 
#
#
#    @property
#    def energy
#        """
#        Current reported energy of the XFEL
#        """
#        return 
#
#
#    @property
#    def repetition_rate
#
#
#    def attenuate
#
#
#    def __copy__
