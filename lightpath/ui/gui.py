"""
Full Application for Lightpath
"""
from functools import partial
import logging
import threading
import os.path

import numpy as np
import pcdsdevices.device_types as dtypes
from pcdsdevices.valve import PPSStopper
from pydm import Display
from qtpy.QtCore import Slot as pyqtSlot, Qt
from qtpy.QtWidgets import QHBoxLayout, QGridLayout, QCheckBox
import typhos
from typhos import TyphosDeviceDisplay

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
    shown_types = [dtypes.Attenuator, dtypes.GateValve, dtypes.IPM,
                   dtypes.LODCM, dtypes.OffsetMirror, dtypes.PIM, PPSStopper,
                   dtypes.PulsePicker, dtypes.Slits, dtypes.Stopper,
                   dtypes.XFLS]

    def __init__(self, controller, beamline=None,
                 parent=None, dark=True):
        super().__init__(parent=parent)
        # Store Lightpath information
        self.light = controller
        self.path = None
        self.detail_screen = None
        self.device_buttons = dict()
        self._lock = threading.Lock()
        # Create empty layout
        self.lightLayout = QHBoxLayout()
        self.lightLayout.setSpacing(1)
        self.widget_rows.setLayout(self.lightLayout)
        self.device_types.setLayout(QGridLayout())
        self.overview.setLayout(QHBoxLayout())
        self.overview.layout().setSpacing(2)
        self.overview.layout().setContentsMargins(2, 2, 2, 2)
        # Setup the fancy overview slider
        slide_scroll = self.scroll.horizontalScrollBar()
        self.slide.setRange(slide_scroll.minimum(),
                            slide_scroll.maximum())
        self.slide.sliderMoved.connect(slide_scroll.setSliderPosition)
        slide_scroll.rangeChanged.connect(self.slide.setRange)
        slide_scroll.valueChanged.connect(self.slide.setSliderPosition)
        # Add destinations
        for line in self.destinations():
            self.destination_combo.addItem(line)

        # Connect signals to slots
        self.destination_combo.currentIndexChanged.connect(
                                            self.change_path_display)
        self.device_combo.activated[str].connect(self.focus_on_device)
        self.impediment_button.pressed.connect(self.focus_on_device)
        self.remove_check.toggled.connect(self.filter)
        self.upstream_check.toggled.connect(self.filter)
        self.detail_hide.clicked.connect(self.hide_detailed)
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
                self.device_buttons[box] = device_type
                box.toggled.connect(self.filter)
        # Setup the UI
        self.change_path_display()
        self.resizeSlider()
        # Change the stylesheet
        if dark:
            typhos.use_stylesheet(dark=True)

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
        # Create two widgets
        widgets = (LightRow(device),
                   LightRow(device))
        # Condense the second
        widgets[1].condense()
        return widgets

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

    @property
    def hidden_devices(self):
        """Device types set to currently be visible"""
        return [dtype for button, dtype in self.device_buttons.items()
                if not button.isChecked()]

    @pyqtSlot()
    @pyqtSlot(bool)
    def change_path_display(self, value=None):
        """
        Change the display devices based on the state of the control buttons
        """
        with self._lock:
            logger.debug("Resorting beampath display ...")
            # Remove old detailed screen
            self.hide_detailed()
            # Grab all the light rows
            rows = [self.load_device_row(d)
                    for d in self.select_devices(self.selected_beamline())]
            # Clear layout if previously loaded rows exist
            if self.rows:
                # Clear our subscribtions
                for row in self.rows:
                    # Remove from layout
                    self.lightLayout.removeWidget(row[0])
                    self.overview.layout().removeWidget(row[1])
                    # Disconnect
                    for widget in row:
                        widget.clear_sub()
                        widget.deleteLater()
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
                self.lightLayout.addWidget(row[0])
                self.overview.layout().addWidget(row[1])
                # Connect condensed widget to focus_on_device
                row[1].device_drawing.clicked.connect(
                        partial(self.focus_on_device,
                                name=row[1].device.name))
                # Connect large widget to show Typhos screen
                row[0].device_drawing.clicked.connect(
                        partial(self.show_detailed, row[0].device))
                # Add device to combo
                self.device_combo.addItem(row[0].device.name)
        # Initialize interface
        for row in self.rows:
            for widget in row:
                widget.update_state()
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
                device = row[0].device
                # If our device is before or at the impediment, it is lit
                if not block or (device.md.z <= block.md.z):
                    _in = True
                    # Check whether this device is passing beam
                    _out = block != device
                # Otherwise, it is off
                else:
                    _in, _out = (False, False)
                # Update widget display
                for widget in row:
                    widget.update_light(_in, _out)

    @pyqtSlot()
    @pyqtSlot(str)
    def focus_on_device(self, name=None):
        """Scroll to the desired device"""
        # If not provided a name, use the impediment
        name = name or self.current_impediment.text()
        # Map of names
        names = [row[0].device.name for row in self.rows]
        # Find index
        try:
            idx = names.index(name)
        except ValueError:
            logger.error("Can not set focus on device %r",
                         name)
            return
        # Grab widget
        self.rows[idx][0].setHidden(False)
        self.scroll.ensureWidgetVisible(self.rows[idx][0])

    @pyqtSlot(bool)
    def filter(self, *args):
        """Hide devices along the beamline for a more succinct view"""
        for row in self.rows:
            device = row[0].device
            # Hide if a hidden instance of a device type
            hidden_device_type = type(device) in self.hidden_devices
            # Hide if removed
            hidden_removed = (not self.remove_check.isChecked()
                              and row[0].last_state == DeviceState.Removed)
            # Hide if upstream
            beamline = self.selected_beamline()
            hidden_upstream = (not self.upstream_check.isChecked()
                               and device.md.beamline != beamline)
            # Hide device if any of the criteria are met
            row[0].setHidden(hidden_device_type
                             or hidden_removed
                             or hidden_upstream)
        # Change the slider size to match changing view
        self.resizeSlider()

    def clear_subs(self):
        """
        Clear the subscription event
        """
        self.path.clear_sub(self.update_path)

    @pyqtSlot()
    def show_detailed(self, device):
        """Show the Typhos display for a device"""
        # Hide the last widget
        self.hide_detailed()
        # Create a Typhos display
        try:
            self.detail_screen = TyphosDeviceDisplay.from_device(device)
        except Exception:
            logger.exception("Unable to create display for %r",
                             device.name)
            return
        # Add to widget
        self.detail_layout.insertWidget(1, self.detail_screen,
                                        0, Qt.AlignHCenter)
        self.device_detail.show()

    @pyqtSlot()
    def hide_detailed(self):
        """Hide Typhos display for a device"""
        # Catch the issue when there is no detail_screen already
        self.device_detail.hide()
        if self.detail_screen:
            # Remove from layout
            self.detail_layout.removeWidget(self.detail_screen)
            # Destroy widget
            self.detail_screen.deleteLater()
            self.detail_screen = None

    def resizeSlider(self):
        # Visible area of beamline
        visible = self.scroll.width() / self.scroll.widget().width()
        # Take same fraction of bar up in handle width
        slider_size = round(self.slide.width() * visible)
        # Set Stylesheet
        self.slide.setStyleSheet('QSlider::handle'
                                 '{width: %spx;'
                                 'background: rgb(124, 252, 0);}'
                                 '' % slider_size)

    def show(self):
        # Comandeered to assure that slider is initialized properly
        super().show()
        self.resizeSlider()

    def resizeEvent(self, evt):
        # Further resize-ing of the widget should affect the fancy slider
        super().resizeEvent(evt)
        self.resizeSlider()
