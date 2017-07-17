"""
Illustrator for drawing the entire Lightpath
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############
import pedl
from pedl.choices import AlignmentChoice
##########
# Module #
##########
from .broadcast import convert
from .widgets   import LightWidget, PipeWidget

logger = logging.getLogger(__name__)


class Illustrator:
    """
    Abstraction for ``pedl.Designer``
    """
    device_spacing = 2

    def __init__(self):
        self.app = pedl.Designer()



    def draw_path(self, beampath):
        """
        Draw a single beampipe layout

        Parameters
        ----------
        beampath : :class:`.BeamPath`
            Path to illustrate in UI

        Returns
        -------
        layout : :class:`pedl.HBoxLayout`:
            Horizontal layout containing all devices
        """
        l = pedl.HBoxLayout(spacing=self.device_spacing,
                            alignment=AlignmentChoice.Center)

        #Draw all the beampipes but the final path
        for i, device in enumerate(beampath.path):
            #Add LightWidget
            l.addLayout(LightWidget(convert(device, with_prefix=True),
                                    name=device.name))
            #Draw beampipe if not last in line
            if device != beampath.devices[-1]:
                l.addLayout(PipeWidget(convert(beampath, with_prefix=True),
                                       i+1, len(beampath.devices)+1))

        return l


    def show(self, wait=True):
        """
        Show the Lightpath UI

        Parameters
        ----------
        wait : bool, optional
           Choice to block the thread while the window is open
        
        Returns
        -------
        proc : subprocess.Popen
            Main window process
        """
        return self.app.exec_(wait=wait)


    def save(self, path):
        """
        Save the Lightpath UI to disk

        Parameters
        ----------
        path : str
            Path to save EDL file 
        """
        if not path.endswith('.edl'):
            path += '.edl'
            logger.warning('No .edl file extension provided, modifying '
                           'file path to {}'.format(path))
        
        with open(path, 'w+') as f:
            self.app.dump(f)
