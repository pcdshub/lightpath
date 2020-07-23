"""
Definitions for Lightpath Widgets
"""
import logging
import os.path

from pydm import Display
from ophyd import Kind
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QBrush, QColor, QFont
from qtpy.QtWidgets import QLabel
import qtawesome as qta
from typhos.utils import (clean_name, get_all_signals_from_device,
                          is_signal_ro)
from typhos.widgets import create_signal_widget

from lightpath.path import find_device_state, DeviceState

logger = logging.getLogger(__name__)

# Define the state colors that correspond to DeviceState
state_colors = [QColor(124, 252, 0),  # Removed
                QColor(255, 0, 0),  # Inserted
                QColor(255, 215, 0),  # Unknown
                QColor(255, 215, 0),  # Disconnected
                QColor(255, 0, 255),  # Disconnected
                QColor(255, 0, 255)]  # Error


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
    ``"fa.square"` is used instead."""
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
    def __init__(self, device, parent=None):
        super().__init__(parent=parent)
        self.device = device
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
        # Hide commands and labels
        self.device_information.hide()
        self.commands.hide()
        # Resize drawings
        self.out_indicator.hide()
        self.device_drawing.setFixedHeight(15)
        self.device_drawing.setMaximumWidth(15)
        self.horizontalWidget.layout().setSpacing(1)
        self.horizontalWidget.setFixedHeight(15)


class LightRow(InactiveRow):
    """
    Basic Widget to display LightDevice information

    The widget shows the device information and state, updating looking at the
    devices :attr:`.inserted` and :attr:`.removed` attributes. The
    :attr:`.remove_button` also allows the user to remove devices by calling
    the :meth:`.remove` method of the given device. The identical button is
    setup if the device is determined to have an `insert` method. Finally,
    PyDMRectangle is used to show the current path of the beam through the
    table

    Parameters
    ----------
    device : obj

    path : BeamPath

    parent : QObject, optional
    """
    MAX_HINTS = 2
    device_updated = Signal()

    def __init__(self, device, parent=None):
        super().__init__(device, parent=parent)
        self.device_updated.connect(self.update_state)

        # Subscribe device to state changes
        try:
            # Wait for later to update widget
            self.device.subscribe(self._update_from_device,
                                  event_type=self.device.SUB_STATE,
                                  run=False)
        except Exception:
            logger.error("Widget is unable to subscribe to device %s",
                         device.name)

        # Add hints for ophyd Device
        def hinted_filter(walk):
            return walk.item.kind == Kind.hinted

        hinted_signals = get_all_signals_from_device(device,
                                                     filter_by=hinted_filter)
        if len(hinted_signals) >= self.MAX_HINTS:
            logger.debug("Device %r has a number of hints exceeding "
                         "%r, not all will be shown",
                         device.name, self.MAX_HINTS)
            hinted_signals = hinted_signals[:self.MAX_HINTS]

        # Add each hint
        for signal in hinted_signals:
            try:
                self.add_signal(signal)
            except Exception:
                logger.exception("Unable to add widget for %r",
                                 signal.name)

    def _update_from_device(self, *args, **kwargs):
        self.device_updated.emit()

    def add_signal(self, signal):
        """Add a signal to the widget display"""
        # Create control widget
        widget = create_signal_widget(signal, read_only=is_signal_ro(signal))
        # Create label widget
        label = QLabel(self)
        bold_font = QFont()
        bold_font.setBold(True)
        label.setFont(bold_font)
        # Add the label
        label.setText(clean_name(signal, strip_parent=self.device.root))
        # Add to the layout
        # Annoying count block because insertWidget does not support negative
        # indexing
        count = self.command_layout.count()
        self.command_layout.insertWidget(count - 1, label, 0, Qt.AlignHCenter)
        self.command_layout.insertWidget(count, widget, 0, Qt.AlignHCenter)

    def update_state(self, *args, **kwargs):
        """
        Update the state label

        The displayed state can be one of ``Unknown`` , ``Inserted``,
        ``Removed`` or ``Error``, with ``Unknown`` being if the device is not
        inserted or removed, and error being if the device is reporting as both
        inserted and removed. The color of the label is also adjusted to either
        green or red to quickly
        """
        # Interpret state
        self.last_state = find_device_state(self.device)
        # Set label to state description
        self.state_label.setText(self.last_state.name)
        color = state_colors[self.last_state.value]
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
        self.device.clear_sub(self.update_state)


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
