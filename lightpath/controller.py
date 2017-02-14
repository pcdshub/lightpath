####################
# Standard Library #
####################
import logging

####################
#    Third Party   #
####################
from happi import Client

####################
#     Package      #
####################
from .utils import PathError

class LightController:
    """
    Controller for the LCLS Lightpath


    Attributes
    ----------
    paths
    devices
    beamlines

    """
    conn = None

    def __init__(self, host, port):

        #Connect to Happi Database
        self.conn    = Client(host=host, port=port)

        #Load devices and beamlines
        #TODO Mapping of containers to devices
        self.devices   =  self.conn.all_devices()
        self.paths     = []
        self.beamlines = dict.from_keys(set([d.beamline
                                             for d in self.devices]),
                                             {'parents' : list(),
                                              'beampath' : None})

        #Create beampaths
        for line in self.beamlines.keys():
            self.beamlines[line]['beampath'] = BeamPath([d
                                                         for d in self.devices
                                                         if d.beamline==line],
                                                         name=line)
        #Map branches
        #TODO catch bad branches
        for (line, branches) in [(d.beamline, d.branching)
                                  for d in self.devices
                                  if d.branching]:
            for branch in branches:
                try:
                    self.beamlines[branch]['branches'].append(line)

                except KeyError:
                    raise PathError('No beamline found with name '
                                    '{}'.format(branch))

        #Create joined beampaths
        for line, info in beamlines.items():

            path = info['beampath']
            if info.get('parents'):
                for source in info['parents']:
                    path.join(self.beamline[source]['beampath'])

            setattr(self, line, path)


    @property
    def destinations(self):
        """
        Current beam destinations
        """
        d = set([p.impediment for p in self.paths if p.impediment])

        if not d:
            return None

        else:
            return d



#    def is_incident(self, device):

#    def find_device(self, *args, **kwargs):
