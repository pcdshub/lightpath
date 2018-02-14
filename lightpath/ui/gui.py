"""
Full Application for Lightpath
"""
############
# Standard #
############
import logging
import threading
import os.path
from functools import partial

###############
# Third Party #
###############
from pydm import Display
from pydm.PyQt.QtCore import pyqtSlot, Qt
from pydm.PyQt.QtGui  import QColor, QSpacerItem, QGridLayout

import happi

##########
# Module #
##########
from .widgets import LightRow, InactiveRow
from ..controller import LightController

logger = logging.getLogger(__name__)

class LightApp(Display):
    """
    Main widget display for the lightpath

    Shows tables of devices and the current destination of the beam, as well
    as the status of the MPS system for LCLS

    Parameters
    ----------
    controller: LightController
        LightController object

    beamline : str, optional
        Beamline to initialize the application with, otherwise the most
        upstream beamline will be selected

    dark : bool, optional
        Load the UI with the `qdarkstyle` interface

    parent : optional
    """

    def __init__(self, controller, beamline=None,
                 parent=None, dark=True):
        super().__init__(parent=parent)
        #Store Lightpath information
        self.light = controller
        self.path  = None
        self._lock = threading.Lock()
        #Create empty layout
        self.lightLayout = QGridLayout()
        self.lightLayout.setVerticalSpacing(1)
        self.lightLayout.setHorizontalSpacing(10)
        self.widget_rows.setLayout(self.lightLayout)

        #Add destinations
        for line in self.destinations():
            self.destination_combo.addItem(line)

        #Connect signals to slots
        self.destination_combo.currentIndexChanged.connect(
                                            self.change_path_display)
        self.upstream_check.clicked.connect(self.change_path_display)
        self.transmission_slider.valueChanged.connect(self.transmission_adjusted)
        #Store LightRow objects to manage subscriptions
        self.rows = list()
        #Select the beamline to begin with
        beamline = beamline or self.destinations()[0]
        try:
            idx = self.destinations().index(beamline.upper())
        except ValueError:
            logger.error("%s is not a valid beamline", beamline)
            idx = 0
        #Move the ComboBox
        self.destination_combo.setCurrentIndex(idx)
        #Setup the UI
        self.change_path_display()

        #Change the stylesheet
        if dark:
            try:
                import qdarkstyle
            except ImportError:
                logger.error("Can not use dark theme, "
                             "qdarkstyle package not available")
            else:
                self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    def destinations(self):
        """
        All possible beamline destinations sorted by end point
        """
        return sorted(list(self.light.beamlines.keys()),
                      key= lambda x : self.light.beamlines[x].range[0])

    def load_device_row(self, device):
        """
        Create LightRow for device
        """
        return LightRow(device, parent=self.widget_rows)

    def select_devices(self, beamline, upstream=True):
        """
        Select a subset of beamline devices to show in the display

        Parameters
        ----------
        beamline : str
            Beamline to display

        upstream : bool, optional
            Include upstream devices in the display
        """
        #Clear any remaining subscriptions
        if self.path:
            self.clear_subs()
        #Find pool of devices and create subscriptions
        self.path = self.light.beamlines[beamline]
        #Defer running updates until UI is created 
        self.path.subscribe(self.update_path, run=False)
        #Only return devices if they are on the specified beamline
        if not upstream:
            pool = [dev for dev in self.path.path
                    if dev.md.beamline == beamline]
        else:
            pool = self.path.path
        logger.debug("Selected %s devices ...", len(pool))
        return pool

    def selected_beamline(self):
        """
        Current beamline selected by the combo box
        """
        return self.destination_combo.currentText()

    def upstream(self):
        """
        Whether the user has selected to display upstream devices
        """
        return self.upstream_check.isChecked()

    @pyqtSlot(bool)
    def remove(self, value, device=None):
        """
        Remove the device from the beamline
        """
        if device:
            logger.info("Removing device %s ...", device.name)
            try:
                device.remove()
            except Exception as exc:
                logger.error(exc)

    @pyqtSlot(bool)
    def insert(self, value, device=None):
        """
        Insert the device from the beamline
        """
        if device:
            logger.info("Inserting device %s ...", device.name)
            try:
                device.insert()
            except Exception as exc:
                logger.error(exc)

    @pyqtSlot(int)
    def transmission_adjusted(self, value):
        """
        Adjust the :attr:`.BeamPath.minimum_transmission`
        """
        logger.debug("Adjusted minimum transmission to %s percent", value)
        self.path.minimum_transmission = value/100.
        self.update_path()

    @pyqtSlot()
    @pyqtSlot(bool)
    def change_path_display(self, value=None):
        """
        Change the display devices based on the state of the control buttons
        """
        with self._lock:
            logger.debug("Resorting beampath display ...")
            #Grab all the light rows
            rows = [self.load_device_row(d)
                    for d in self.select_devices(self.selected_beamline(),
                                                 upstream=self.upstream())]
            #Clear layout if previously loaded rows exist
            if self.rows:
                #Clear our subscribtions
                for row in self.rows: row.clear_sub()
                #Clear the widgets
                for i in reversed(range(self.lightLayout.count())):
                    old = self.lightLayout.takeAt(i).widget()
                    if old:
                        old.deleteLater()
                #Clear subscribed row cache
                self.rows.clear()

            #Add all the widgets to the display
            for i, row in enumerate(rows):
                #Cache row to later clear subscriptions
                self.rows.append(row)
                #Connect up remove button
                if hasattr(row, 'remove_button'):
                    row.remove_button.clicked.connect(partial(self.remove,
                                                              device=row.device))
                #Connect up insert button
                if hasattr(row, 'insert_button'):
                    row.insert_button.clicked.connect(partial(self.insert,
                                                              device=row.device))
                #Add widgets to layout
                for j, widget in enumerate(row.widgets):
                    if isinstance(widget, QSpacerItem):
                        self.lightLayout.addItem(widget, i, j)
                    else:
                        self.lightLayout.addWidget(widget, i, j)
        #Initialize interface
        for row in self.rows:
            row.update_state()
        #Update display
        self.transmission_adjusted(self.transmission_slider.value()) #Calls .update_path

    def ui_filename(self):
        """
        Name of designer UI file
        """
        return 'lightapp.ui'

    def ui_filepath(self):
        """
        Full path to :attr:`.ui_filename`
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            self.ui_filename())

    def update_path(self, *args,  **kwargs):
        """
        Update the PyDMRectangles to show devices as in the beam or not
        """
        with self._lock:
            block = self.path.impediment
            for row in self.rows:
                #If our device is before or at the impediment, it is lit
                if not block or (row.device.md.z <= block.md.z):
                    row.indicator._default_color = Qt.cyan
                #Otherwise, it is off
                else:
                    row.indicator._default_color = Qt.gray
                #Update widget display
                row.indicator.update()

    def clear_subs(self):
        """
        Clear the subscription event
        """
        self.path.clear_sub(self.update_path)
