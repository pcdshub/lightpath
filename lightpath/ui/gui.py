"""
Full Application for Lightpath
"""
############
# Standard #
############
import logging
from os import path
from functools import partial

###############
# Third Party #
###############
from pydm import Display
from pydm.PyQt.QtCore import pyqtSlot, Qt
from pydm.PyQt.QtGui  import QSpacerItem, QGridLayout
from pydm.widgets.drawing import PyDMDrawingLine

import happi
from happi import Client
from happi.backends import JSONBackend
from pcdsdevices.happireader import construct_device

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
    *args
        List of instantiated devices that match :class:`.LightInterface`

    containers : list, optional
        Happi device containers to display in the GUI but not to use in the
        lightpath logic

    beamline : str, optional
        Beamline to initialize the application with, otherwise the most
        upstream beamline will be selected

    dark : bool, optional
        Load the UI with the `qdarkstyle` interface

    parent : optional
    """

    def __init__(self, *devices, containers=None, beamline=None,
                 parent=None, dark=True):
        super().__init__(parent=parent)
        #Store Lightpath information
        self.light = LightController(*devices)
        self.path  = None
        #Create empty layout
        self.lightLayout = QGridLayout(self.widget_rows)
        self.lightLayout.setVerticalSpacing(1)
        self.lightLayout.setHorizontalSpacing(1)
        self.widget_rows.setLayout(self.lightLayout)
        self.scroll.setWidget(self.widget_rows)

        #Add destinations
        for line in self.destinations():
            self.destination_combo.addItem(line)

        #Connect signals to slots
        self.destination_combo.currentIndexChanged.connect(
                                            self.change_path_display)
        self.mps_only_check.clicked.connect(self.change_path_display)
        self.upstream_check.clicked.connect(self.change_path_display)
        #Store LightRow objects to manage subscriptions
        self.rows = list()
        #Select the beamline to begin with
        beamline = beamline or self.destinations()[0]
        try:
            idx = self.destinations().index(beamline)
        except ValueError:
            logger.error("%s is not a valid beamline", beamline)
            idx = 0
        #Move the ComboBox
        self.destination_combo.setCurrentIndex(idx)
        #Grab containers
        containers = containers or []
        self.containers = dict((key, list())
                               for key in self.light.beamlines.keys())
        for device in containers:
            try:
                #Check we have a z attribute
                z = getattr(device, 'z')
                self.containers[device.beamline].append(device)
            except KeyError:
                logger.error('Container %s belongs to beamline %s, '
                             ' which is not represented by other devices',
                             device.name, device.beamline)
            except AttributeError:
                logger.error('Device %r does not implement the proper '
                             'interface to be included in the path',
                             device)
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

    @property
    def device_rows(self):
        """
        Subset of device rows that refer to live devices
        """
        return [row for row in self.rows if not isinstance(row.device,
                                                           happi.Device)]

    def load_device_row(self, device):
        """
        Create LightRow for device
        """
        #Create new widget
        if isinstance(device, happi.Device):
            w = InactiveRow(device, parent=self.widget_rows)
        else:
            w = LightRow(device, parent=self.widget_rows)
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
        #Clear any remaining subscriptions
        if self.path:
            self.clear_subs()
        #Find pool of devices and create subscriptions
        self.path = self.light.beamlines[beamline]
        #Defer running updates until UI is created 
        self.path.subscribe(self.update_path, run=False)
        self.path.subscribe(self.update_mps,
                            event_type=self.path.SUB_MPSPATH_CHNG,
                            run=False)
        pool = self.path.path
        #Find end point for each beamline
        bls  = set(d.beamline for d in pool)
        endpoints = dict((bl, max([d.z for d in pool
                                   if d.beamline == bl]))
                         for bl in bls)
        #Find necessary containers
        containers = [c for bl in endpoints.keys()
                        for c in self.containers[bl]
                        if (c.beamline == bl
                            and c.z < endpoints[bl])]
        #Add containers to pool and resort
        pool = sorted(pool + containers, key = lambda x : x.z)
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

    @pyqtSlot(bool)
    def remove(self, value, device=None):
        """
        Remove the device from the beamline
        """
        if device:
            logger.info("Removing device %s ...", device.name)
            try:
                device.remove(wait=False)
            except Exception as exc:
                logger.error(exc)


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
            #Add widgets to layout
            for j, widget in enumerate(row.widgets):
                if isinstance(widget, QSpacerItem):
                    self.lightLayout.addItem(widget, i, j)
                else:
                    self.lightLayout.addWidget(widget, i, j)
        #Initialize interface
        self.update_path()
        self.update_mps()

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

    def update_path(self, *args,  **kwargs):
        """
        Update the PyDMRectangles to show devices as in the beam or not
        """
        block = self.path.impediment
        for row in self.device_rows:
            #If our device is before or at the impediment, it is lit
            if not block or (row.device.z <= block.z):
                row.indicator._default_color = Qt.cyan
            #Otherwise, it is off
            else:
                row.indicator._default_color = Qt.gray
            #Update widget display
            row.indicator.update()

    def update_mps(self, *args, **kwargs):
        """
        Update the MPS status of the frame

        The frame of the row will be red if the device is tripping the beam,
        yellow if it is faulted but a full trip is being prevented by an
        upstream device
        """
        #Path information
        tripped = self.path.tripped_devices
        faulted = self.path.faulted_devices
        for row in self.device_rows:
            if row.device in tripped:
                row.frame.setStyleSheet("#name_frame {border: 2px solid red}")
            elif row.device in faulted:
                row.frame.setStyleSheet("#name_frame {border: 2px "\
                                         "solid rgb(255,215,0)}")
            else:
                row.frame.setStyleSheet("#frame {border: 0px solid black}")

    def clear_subs(self):
        """
        Clear the subscription event
        """
        self.path.clear_sub(self.update_path)
        self.path.clear_sub(self.update_mps)
