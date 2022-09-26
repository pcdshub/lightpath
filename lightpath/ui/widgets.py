"""
Definitions for Lightpath Widgets
"""
import logging
import os.path

import qtawesome as qta
from pydm import Display
from qtpy.QtCore import Signal
from qtpy.QtGui import QBrush, QColor
from qtpy.QtWidgets import QLabel
from typhos.utils import clean_name

from lightpath.path import DeviceState, find_device_state

logger = logging.getLogger(__name__)

# Define the state colors that correspond to DeviceState
state_colors = {
    'removed': QColor(124, 252, 0),  # Removed (green)
    'half_removed': QColor(0, 176, 255),  # half-removed (light blue)
    'blocking': QColor(255, 0, 0),  # Inserted (red)
    'unknown': QColor(255, 215, 0),  # Unknown (yellow)
    'inconsistent': QColor(255, 215, 0),  # Inconsistent (yellow)
    'disconnected': QColor(255, 0, 255),  # Disconnected (purple)
    'error': QColor(255, 0, 255)  # Error (purple)
}


def to_stylesheet_color(color):
    """Utility to convert QColor to stylesheet specification"""
    return 'rgb({!r}, {!r}, {!r})'.format(color.red(),
                                          color.green(),
                                          color.blue())


def symbol_for_device(device):
    """
    Find a symbol for the ophyd.Device

    This depends on the hidden attribute ``_icon`` that specifies a valid icon
    name to be loaded by the ``qtawesome`` library. If no icon is specified,
    ``"fa.square"`` is used instead."""
    try:
        symbol = getattr(device, '_icon')
    except AttributeError:
        logger.debug("No symbol found %s", device.name)
        symbol = 'fa.square'
    return symbol


class InactiveRow(Display):
    """
    Inactive row for happi container
    """
    def __init__(self, device, path, parent=None):
        super().__init__(parent=parent)
        self.device = device
        self.path = path
        # Initialize prior state variable
        self.last_state = DeviceState.Disconnected
        # Create labels
        self.name_label.setText(clean_name(device, strip_parent=False))
        self.prefix_label.setText('({})'.format(device.prefix))
        # By default we mark the device as Disconnected
        self.state_label.setText('Disconnected')
        self.state_label.setStyleSheet("QLabel {color : rgb(255,0,255)}")
        self.device_drawing = DeviceWidget(device)
        self.horizontalWidget.layout().insertWidget(1, self.device_drawing)

    def ui_filename(self):
        """
        Name of designer UI file
        """
        return 'device.ui'

    def ui_filepath(self):
        """
        Full path to :attr:`.ui_filename`
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            self.ui_filename())

    def clear_sub(self):
        """
        Implemented by rows that have subscriptions
        """
        pass

    def condense(self):
        """Reduce the size of the widget when the device is hidden"""
        # Hide labels
        self.device_information.hide()
        # Resize drawings
        self.out_indicator.hide()
        self.device_drawing.setFixedHeight(15)
        self.device_drawing.setMaximumWidth(15)
        self.horizontalWidget.layout().setSpacing(1)
        # give pixmap enough room to not clip
        self.horizontalWidget.setFixedHeight(20)


class LightRow(InactiveRow):
    """
    Basic Widget to display LightDevice information

    The widget shows the device information and state, updating looking at the
    device in the context of the path it resides in The device provided is
    expected to implement the ``LightpathMixin`` interface provided in
    ``pcdsdevices``.  This widget subscribes to the device's
    ``lightpath_summary`` signal for updates.  Finally, PyDMRectangle is used
    to show the current path of the beam through the table.

    Parameters
    ----------
    device : obj

    path : BeamPath

    parent : QObject, optional
    """
    MAX_HINTS = 2
    device_updated = Signal()

    def __init__(self, device, path, parent=None):
        super().__init__(device, path, parent=parent)
        self.device_updated.connect(self.update_state)

        # Subscribe device to state changes
        try:
            # Wait for later to update widget
            logger.debug(f"Subscribing widget to device {self.device.name}")
            self.device.lightpath_summary.subscribe(
                self._update_from_device,
                run=False
            )
        except Exception:
            logger.error("Widget is unable to subscribe to device %s",
                         device.name)

    def _update_from_device(self, *args, **kwargs):
        self.device_updated.emit()

    def get_state_color(self) -> QColor:
        """
        Determine the icon color given the device state and path status
        If device is an impediment: state_color['blocking']
        If device is removed: state_color['removed']
        If device is in, not blocking (mirrors): state_color['half_removed']
        If device is unknown / errored: state_color['error']

        The color of the labels should quickly point users to blocking devices,
        while providing useful information about each device's state.

        Could take a color map in the future?  Colorblind support?

        Returns
        -------
        QColor
            the color to apply to the icon
        """
        device_state, _ = find_device_state(self.device)
        blocking_devices = self.path.blocking_devices

        if device_state is DeviceState.Disconnected:
            return state_colors['disconnected']
        if device_state is DeviceState.Error:
            return state_colors['error']
        if device_state is DeviceState.Inserted:
            if self.device not in blocking_devices:
                return state_colors['half_removed']
            else:
                return state_colors['blocking']
        if device_state is DeviceState.Removed:
            return state_colors['removed']

        return state_colors['unknown']

    def update_state(self, *args, **kwargs):
        """
        Update the state label

        Icon color is determined by ``LightRow.get_state_color()``.
        """
        # Interpret state
        self.last_state = find_device_state(self.device)[0]
        # Set label to state description
        self.state_label.setText(self.last_state.name)
        color = self.get_state_color()
        style_color = to_stylesheet_color(color)
        style_sheet = "QLabel {color: %s}" % style_color
        self.state_label.setStyleSheet(style_sheet)
        self.device_drawing.setColor(color)

    def update_light(self, _in, _out):
        """Update the light beams striking and emitting from the device"""
        for (widget, state) in zip((self.beam_indicator, self.out_indicator),
                                   (_in, _out)):
            # Set color
            if state:
                widget.brush = QBrush(QColor('#00ffff'))
            else:
                widget.brush = QBrush(QColor('#a0a0a4'))

    def clear_sub(self):
        """
        Clear the subscription event
        """
        self.device.lightpath_summary.clear_sub(self._update_from_device)


class DeviceWidget(QLabel):
    """
    Colored Symbol for Lightpath Display

    See :func:`.symbol_for_device` for more information on how the proper
    symbol for the provided device is determined.

    Parameters
    ----------
    device: ophyd.Device
        Object that will have a drawing created for it.
    """
    clicked = Signal()

    def __init__(self, device, parent=None):
        super().__init__(parent=parent)
        # Grab the symbol of the device
        # NOTE: The symbol will not actually be created until setColor is
        # called. We want to avoid unnecessary widget creation and there is no
        # point in drawing a widget until we know more about the state of the
        # device
        self.symbol = symbol_for_device(device)
        # Default UI settings for conformity
        self.setMinimumSize(10, 10)
        self.setMaximumSize(50, 50)
        self.setStyleSheet('padding : 0px')

    def setColor(self, color):
        """
        Set the color of the QIcon contained in the widget
        """
        try:
            icon = qta.icon(self.symbol, color=color)
        # Capture any errors loading icons
        except Exception:
            logger.exception("Unable to load icon %r", self.symbol)
            return
        # Set the proper pixmap
        self.setPixmap(icon.pixmap(self.width(), self.height()))

    def mousePressEvent(self, evt):
        """Catch mousePressEvent to emit "`clicked`" Signal"""
        # Push MouseEvent through
        super().mousePressEvent(evt)
        # Emit click
        self.clicked.emit()
