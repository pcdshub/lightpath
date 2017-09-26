"""
Full Application for Lightpath
"""
############
# Standard #
############
import logging
from os import path

###############
# Third Party #
###############
from pydm import Display
from pydm.PyQt.QtCore import pyqtSlot
from pydm.PyQt.QtGui  import QPushButton, QWidget, QVBoxLayout

from happi import Client
from happi.backends import JSONBackend
from pcdsdevices.happireader import construct_device

##########
# Module #
##########
from .widgets import LightRow
from ..controller import LightController

logger = logging.getLogger(__name__)

class LightApp(Display):
    """
    Main widget display for the lightpath

    Shows tables of devices and the current destination of the beam, as well
    as the status of the MPS system for LCLS

    Parameters
    ----------
    *args
        List of instantiated devices that match :class:`.LightInterface`

    beamline : str, optional
        Beamline to initialize the application with, otherwise the most
        upstream beamline will be selected

    parent : optional
    """

    def __init__(self, *devices, beamline=None,  parent=None):
        super().__init__(parent=parent)
        self.light   = LightController(*devices)
        #Create empty layout
        self.rowLayout = QVBoxLayout(self)
        self.rowLayout.setSpacing(1)
        self.widget_rows.setLayout(self.rowLayout)
        self.scroll.setWidget(self.widget_rows)

        #Add destinations
        for line in self.destinations():
            self.destination_combo.addItem(line)

        #Connect signals to slots
        self.destination_combo.currentIndexChanged.connect(
                                            self.change_path_display)
        self.mps_only_check.clicked.connect(self.change_path_display)
        self.upstream_check.clicked.connect(self.change_path_display)
        #Select the beamline to begin with
        beamline = beamline or self.destinations()[0]
        try:
            idx = self.destinations().index(beamline)
        except ValueError:
            logger.error("%s is not a valid beamline", beamline)
            idx = 0
        #Move the ComboBox
        self.destination_combo.setCurrentIndex(idx)
        #Setup the UI
        self.change_path_display()

    def destinations(self):
        """
        All possible beamline destinations sorted by end point
        """
        return sorted(list(self.light.beamlines.keys()),
                      key= lambda x : self.light.beamlines[x].range[1])

    def load_device_row(self, device):
        """
        Create LightRow for device
        """
        #Create new widget
        w = LightRow(device,
                     self.light.beamlines[device.beamline],
                     parent=self.widget_rows)
        return w

    def select_devices(self, beamline, upstream=True, mps_only=False):
        """
        Select a subset of beamline devices to show in the display

        Parameters
        ----------
        beamline : str
            Beamline to display

        upstream : bool, optional
            Include upstream devices in the display

        mps_only : bool ,optional
            Only show devices that are in the mps system
        """
        pool = self.light.beamlines[beamline].path
        #Only return devices if they are on the specified beamline
        if not upstream:
            pool = [dev for dev in pool if dev.beamline == beamline]
        #Only return MPS devices
        if mps_only:
            #Note: This does not account for improperly configured `mps`
            pool = [dev for dev in pool if hasattr(dev, 'mps')]
        logger.debug("Selected %s devices ...", len(pool))
        return pool

    def selected_beamline(self):
        """
        Current beamline selected by the combo box
        """
        return self.destination_combo.currentText()

    def mps_only(self):
        """
        Whether the user has selected to only display MPS devices
        """
        return self.mps_only_check.isChecked()

    def upstream(self):
        """
        Whether the user has selected to display upstream devices
        """
        return self.upstream_check.isChecked()

    @pyqtSlot()
    @pyqtSlot(bool)
    def change_path_display(self, value=None):
        """
        Change the display devices based on the state of the control buttons
        """
        logger.debug("Resorting beampath display ...")
        #Grab all the light rows
        rows = [self.load_device_row(d)
                for d in self.select_devices(self.selected_beamline(),
                                             upstream=self.upstream(),
                                             mps_only=self.mps_only())]
        #Clear the layout
        for i in reversed(range(self.rowLayout.count())):
            oldrow = self.rowLayout.itemAt(i).widget()
            oldrow.clear_sub()
            self.rowLayout.removeWidget(oldrow)
            oldrow.deleteLater()


        #Add all the widgets to the display
        for row in rows:
            self.rowLayout.addWidget(row)

    def ui_filename(self):
        """
        Name of designer UI file
        """
        return 'lightapp.ui'

    def ui_filepath(self):
        """
        Full path to :attr:`.ui_filename`
        """
        return path.join(path.dirname(path.realpath(__file__)),
                         self.ui_filename())

    @classmethod
    def from_json(cls, json, beamline=None, parent=None,  **kwargs):
        """
        Create a lightpath user interface from a JSON happi database

        Parameters
        ----------
        path : str
            Path to the JSON file

        beamline : str, optional
            Name of beamline to launch application

        parent : QWidget, optional
            Parent for LightApp QWidget

        kwargs :
            Restrict the devices included in the lightpath. These keywords are
            all passed to :meth:`.happi.Client.search`
        
        Returns
        -------
        lightApp:
            Instantiated widget 
        """
        #Load all of the information from happi
        happi   = Client(database=JSONBackend(json))
        devices = happi.search(**kwargs, as_dict=False)
        #Create valid pcdsdevices
        path = list()
        for dev in devices:
            try:
                path.append(construct_device(dev))
            except Exception:
                logger.exception("Error instantiating %s ...", dev.name)
        #Instantiate the Application
        logger.debug("Instantiating User Interface ...")
        return cls(*path, beamline=beamline, parent=parent)



