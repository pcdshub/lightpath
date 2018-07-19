"""
Full Application for Lightpath
"""
from functools import partial
import logging
import threading
import os.path

import numpy as np
from pcdsdevices.device_types import *  # noqa
from pydm import Display
from pydm.PyQt.QtCore import pyqtSlot, Qt
from pydm.PyQt.QtGui import QHBoxLayout, QGridLayout, QCheckBox

from lightpath.path import DeviceState
from .widgets import LightRow

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
    shown_types = [Attenuator, IPM, XFLS, LODCM, OffsetMirror, PIM,  # noqa
                   PulsePicker, Slits, Stopper, GateValve]  # noqa

    def __init__(self, controller, beamline=None,
                 parent=None, dark=True):
        super().__init__(parent=parent)
        # Store Lightpath information
        self.light = controller
        self.path = None
        self._lock = threading.Lock()
        # Create empty layout
        self.lightLayout = QHBoxLayout()
        self.lightLayout.setSpacing(1)
        self.widget_rows.setLayout(self.lightLayout)
        self.device_types.setLayout(QGridLayout())
        # Add destinations
        for line in self.destinations():
            self.destination_combo.addItem(line)

        # Connect signals to slots
        self.destination_combo.currentIndexChanged.connect(
                                            self.change_path_display)
        self.device_combo.activated[str].connect(self.focus_on_device)
        self.impediment_button.pressed.connect(self.focus_on_device)
        self.remove_check.toggled.connect(self.show_removed)
        self.upstream_check.toggled.connect(self.show_upstream)
        # Store LightRow objects to manage subscriptions
        self.rows = list()
        # Select the beamline to begin with
        beamline = beamline or self.destinations()[0]
        try:
            idx = self.destinations().index(beamline.upper())
        except ValueError:
            logger.error("%s is not a valid beamline", beamline)
            idx = 0
        # Move the ComboBox
        self.destination_combo.setCurrentIndex(idx)
        # Add all of our device type options
        max_columns = 3
        for i, row in enumerate(np.array_split(self.shown_types,
                                               max_columns)):
            for j, device_type in enumerate(row):
                # Add box to layout
                box = QCheckBox(device_type.__name__)
                box.setChecked(True)
                self.device_types.layout().addWidget(box, j, i)
                # Hook up box to hide function
                box.toggled.connect(partial(self.show_devicetype,
                                            device=device_type))
        # Setup the UI
        self.change_path_display()

        # Change the stylesheet
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
                      key=lambda x: self.light.beamlines[x].range[0])

    def load_device_row(self, device):
        """
        Create LightRow for device
        """
        return LightRow(device, parent=self.widget_rows)

    def select_devices(self, beamline):
        """
        Select a subset of beamline devices to show in the display

        Parameters
        ----------
        beamline : str
            Beamline to display

        upstream : bool, optional
            Include upstream devices in the display
        """
        # Clear any remaining subscriptions
        if self.path:
            self.clear_subs()
        # Find pool of devices and create subscriptions
        self.path = self.light.beamlines[beamline]
        # Defer running updates until UI is created
        self.path.subscribe(self.update_path, run=False)
        logger.debug("Selected %s devices ...", len(self.path.path))
        return self.path.path

    def selected_beamline(self):
        """
        Current beamline selected by the combo box
        """
        return self.destination_combo.currentText()

    @pyqtSlot()
    @pyqtSlot(bool)
    def change_path_display(self, value=None):
        """
        Change the display devices based on the state of the control buttons
        """
        with self._lock:
            logger.debug("Resorting beampath display ...")
            # Grab all the light rows
            rows = [self.load_device_row(d)
                    for d in self.select_devices(self.selected_beamline())]
            # Clear layout if previously loaded rows exist
            if self.rows:
                # Clear our subscribtions
                for row in self.rows:
                    row.clear_sub()
                    self.lightLayout.removeWidget(row)
                    row.deleteLater()
                # Clear subscribed row cache
                self.rows.clear()
                self.device_combo.clear()

            # Hide nothing when switching beamlines
            boxes = self.device_types.children()
            boxes.extend([self.upstream_check, self.remove_check])
            for box in boxes:
                if isinstance(box, QCheckBox):
                    box.setChecked(True)
            # Add all the widgets to the display
            for i, row in enumerate(rows):
                # Cache row to later clear subscriptions
                self.rows.append(row)
                # Add widget to layout
                self.lightLayout.addWidget(row)
                # Add device to combo
                self.device_combo.addItem(row.device.name)
        # Initialize interface
        for row in self.rows:
            row.update_state()
        # Update the state of the path
        self.update_path()

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
            # Set the current impediment label
            if block:
                self.current_impediment.setText(block.name)
                self.impediment_button.setEnabled(True)
            else:
                self.current_impediment.setText('None')
                self.impediment_button.setEnabled(False)
            for row in self.rows:
                # If our device is before or at the impediment, it is lit
                if not block or (row.device.md.z <= block.md.z):
                    # This device is being hit by the beam
                    row.beam_indicator._default_color = Qt.cyan
                    # Check whether this device is passing beam
                    if block != row.device:
                        row.out_indicator._default_color = Qt.cyan
                    else:
                        row.out_indicator._default_color = Qt.gray
                # Otherwise, it is off
                else:
                    row.beam_indicator._default_color = Qt.gray
                    row.out_indicator._default_color = Qt.gray
                # Update widget display
                row.beam_indicator.update()
                row.out_indicator.update()

    @pyqtSlot()
    @pyqtSlot(str)
    def focus_on_device(self, name=None):
        """Scroll to the desired device"""
        # If not provided a name, use the impediment
        name = name or self.current_impediment.text()
        # Map of names
        names = [row.device.name for row in self.rows]
        # Find index
        try:
            idx = names.index(name)
        except ValueError:
            logger.error("Can not set focus on device %r",
                         name)
            return
        # Grab widget
        self.rows[idx].setHidden(False)
        self.scroll.ensureWidgetVisible(self.rows[idx])

    @pyqtSlot(bool)
    def show_devicetype(self, show, device):
        """Show or hide all instances of a specific row"""
        self._filter(show, lambda x: type(x.device) == device)

    @pyqtSlot(bool)
    def show_removed(self, show):
        """Show or hide all instances of a specific device"""
        self._filter(show, lambda x: x.last_state == DeviceState.Removed)

    @pyqtSlot(bool)
    def show_upstream(self, show):
        """Show or hide upstream devices from the destination beamline"""
        beamline = self.selected_beamline()
        self._filter(show, lambda x: x.device.md.beamline != beamline)

    def _filter(self, show, func):
        """Helper function to hide a device based on a condition"""
        for row in self.rows:
            if func(row):
                row.setVisible(show)

    def clear_subs(self):
        """
        Clear the subscription event
        """
        self.path.clear_sub(self.update_path)
