import logging
from happi import Client

class LightController:
    """
    Controller for the LCLS Lightpath

    """
    conn = None

    def __init__(self, host, port):

        #Connect to Happi Database
        self.conn    = Client(host=host, port=port)

        #Load devices and beamlines
        #TODO Mapping of containers to devices
        self.devices   =  self.conn.all_devices()
        self.beamlines = dict.from_keys(set([d.beamline
                                             for d in self.devices]),
                                             {'parents' : list(),
                                              'beampath' : None})


        #Create beampaths
        for line in self.beamlines.keys():
            self.beamlines[line]['beampath'] = BeamPath([d
                                                         for d  in self.devices
                                                         if d.beamline ==line],
                                                         name=line)
        #Map branches
        #TODO catch bad branches
        for (line, branches) in [(d.beamline, d.branching)
                                  for d in self.devices
                                  if d.branching]:
            for branch in branches:
                self.beamlines[branch]['branches'].append(line)


        #Create joined beampaths
        for line, info in beamlines.items():

            path = info['beampath']
            if info.get('parents'):
                for source in info['parents']:
                    path.join(self.beamline[source]['beampath'])

            setattr(self, line, path)
