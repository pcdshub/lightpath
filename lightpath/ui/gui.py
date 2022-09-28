"""
Full Application for Lightpath
"""
import contextlib
import logging
import os.path
import threading
from functools import partial

import numpy as np
import qtawesome as qta
import typhos
from pydm import Display
from qtpy.QtCore import Qt
from qtpy.QtCore import Slot as pyqtSlot
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QApplication, QCheckBox, QDialog, QGridLayout,
                            QHBoxLayout, QLabel, QVBoxLayout)
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
    def __init__(self, controller, beamline=None,
                 parent=None, dark=True):
        super().__init__(parent=parent)
        # Store Lightpath information
        self.loading_splash = LoadingSplash(parent=self)
        self.light = controller
        self.path = None
        self.detail_screen = None
        self.device_buttons = dict()
        self._lock = threading.Lock()
        self._prev_block = None
        # Create empty layout
        self.lightLayout = QHBoxLayout()
        self.lightLayout.setSpacing(1)
        self.widget_rows.setLayout(self.lightLayout)
        self.device_types.setLayout(QGridLayout())
        self.device_types.layout().setVerticalSpacing(2)
        self.overview.setLayout(QHBoxLayout())
        self.overview.layout().setSpacing(4)
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
        self.upstream_device_combo.activated[str].connect(self.update_upstream)
        self.remove_check.toggled.connect(self.filter)
        self.detail_hide.clicked.connect(self.hide_detailed)
        self.refresh_button.clicked.connect(self.change_path_display)

        # Store LightRow objects to manage subscriptions
        self.rows = list()
        # store device type filter widgets
        self._device_checkboxes = list()
        # Select the beamline to begin with
        beamline = beamline or self.destinations()[0]
        try:
            idx = self.destinations().index(beamline.upper())
        except ValueError:
            logger.error("%s is not a valid beamline", beamline)
            idx = 0
        # Move the ComboBox
        self.destination_combo.setCurrentIndex(idx)
        # Setup the UI
        self.change_path_display()
        self.resizeSlider()
        # Change the stylesheet
        if dark:
            typhos.use_stylesheet(dark=True)

    def destinations(self):
        """
        All possible beamline destinations that have an associated path
        """
        return [line for line in self.light.beamlines.keys()
                if self.light.beamlines[line]]

    def load_device_row(self, device):
        """
        Create LightRow for device
        """
        # Create two widgets
        widgets = (LightRow(device, self.path),
                   LightRow(device, self.path))
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
        self.path = self.light.active_path(beamline)
        # Defer running updates until UI is created
        self.path.subscribe(self.update_path, run=False)
        logger.debug("Selected %s devices ...", len(self.path.path))
        return self.path.path

    def selected_beamline(self):
        """
        Current beamline selected by the combo box
        """
        return self.destination_combo.currentText()

    def selected_upstream_from(self):
        """
        Current device selected by upstream combo box
        """
        return self.upstream_device_combo.currentText()

    @property
    def hidden_devices(self):
        """Device types set to currently be visible"""
        return [dtype for button, dtype in self.device_buttons.items()
                if not button.isChecked()]

    def update_device_types(self):
        """
        Update the device type filter check boxes bases on devices
        currently in the path
        """
        with self._lock:
            valid_types = {}
            for dev in self.path.path:
                mod_name = dev.__module__
                valid_types[(mod_name.split('.', 1)[1])] = mod_name

            # clear old checkboxes
            for child in self._device_checkboxes:
                self.device_types.layout().removeWidget(child)
                self.device_buttons.pop(child)
                child.deleteLater()

            self._device_checkboxes.clear()

            # populate grid with available device types
            max_columns = 3
            for i, row in enumerate(np.array_split(list(valid_types.items()),
                                                   max_columns)):
                for j, device_type in enumerate(row):
                    # Add box to layout
                    box = QCheckBox(device_type[0])
                    box.setChecked(True)
                    self.device_types.layout().addWidget(box, j, i)
                    # Hook up box to hide function
                    self.device_buttons[box] = device_type[1]
                    box.toggled.connect(self.filter)
                    self._device_checkboxes.append(box)

    @pyqtSlot()
    @pyqtSlot(bool)
    def change_path_display(self, value=None):
        """
        Change the display devices based on the state of the control buttons
        """
        with self._lock, self.open_splash(f'{self.selected_beamline()} path'):
            logger.debug("Resorting beampath display ...")
            # Remove old detailed screen
            self.hide_detailed()

            # Clear layout if previously loaded rows exist
            if self.rows:
                # Clear our subscribtions
                logger.debug('clear existing subscriptions')
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
                self.upstream_device_combo.clear()

            # Grab all the light rows (self.path set here)
            rows = [self.load_device_row(d)
                    for d in self.select_devices(self.selected_beamline())]
            # Add all the widgets to the display
            logger.debug('Add widgets to display')
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
                self.upstream_device_combo.addItem(row[0].device.name)
        # Initialize interface
        for row in self.rows:
            for widget in row:
                widget.update_state()
        # Update the state of the path
        self.update_path()
        # Update device type checkboxes
        self.update_device_types()
        self.setWindowTitle(f'Lightpath - {self.selected_beamline()}')

    @contextlib.contextmanager
    def open_splash(self, msg: str):
        """
        Context manager for opening the loading splash screen, and
        closing it always

        Parameters
        ----------
        msg : str
            message to show in the loading screen
        """
        try:
            self.loading_splash.move(self.geometry().center()
                                     - self.loading_splash.rect().center())
            self.loading_splash.show()
            self.loading_splash.update_status(msg)
            yield

        finally:
            self.loading_splash.hide()

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
                    # Reconsider blocking device state
                    if (device is self._prev_block or device is block):
                        widget.update_state()

            self._prev_block = block

    def _destroy_lightpath_summary_signals(self, *args, **kwargs):
        """ Update all widgets in rows """
        # destroy all signals
        logger.debug('destroying all lightpath_summary signals')
        for row in self.rows:
            row[0].device.lightpath_summary.destroy()
            row[1].device.lightpath_summary.destroy()

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

    @pyqtSlot(str)
    def update_upstream(self, name=None):
        self.filter()

    @pyqtSlot(bool)
    def filter(self, *args):
        """Hide devices along the beamline for a more succinct view"""
        # grab device z from upstream combo
        upstream_device = self.selected_upstream_from()
        upstream_device_z = self.light.get_device(upstream_device).md.z
        for row in self.rows:
            device = row[0].device
            # Hide if a hidden instance of a device type
            hidden_device_type = any([device.__module__ == dtype
                                      for dtype in self.hidden_devices])
            # Hide if removed
            hidden_removed = (not self.remove_check.isChecked()
                              and row[0].last_state == DeviceState.Removed)
            # Hide if upstream
            # TODO: This now looks at the whole active path, which includes
            # upstream devices.  Need to figure out how best to define
            # "upstream" devices now.  Possibly by branch name?
            hidden_upstream = (device.md.z < upstream_device_z)
            # Hide device if any of the criteria are met
            row[0].setHidden(hidden_device_type
                             or hidden_removed
                             or hidden_upstream)
        # Change the slider size to match changing view
        self.resizeSlider()

    def clear_subs(self):
        """
        Clear BeamPath-related subscription events
        """
        self.path.clear_sub(self.update_path)
        self.path.clear_device_subs()

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

    def closeEvent(self, a0) -> None:
        self._destroy_lightpath_summary_signals()
        return super().closeEvent(a0)


class LoadingSplash(QDialog):
    """ simple loading splash screen """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)

        self.setStyleSheet("QDialog { border: 2px solid; "
                           "border-color:#00ffff }")
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.status_display = QLabel()
        loading = QLabel()
        loading_icon = qta.icon('ri.loader-2-fill', color=QColor(0, 176, 255))
        loading.setPixmap(loading_icon.pixmap(self.height(), self.height()))

        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_display)
        status_layout.addWidget(loading)

        layout.addLayout(status_layout)

    def update_status(self, msg):
        self.status_display.setText(f"Loading: {msg}")
        QApplication.instance().processEvents()
