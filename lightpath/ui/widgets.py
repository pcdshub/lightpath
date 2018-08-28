"""
Definitions for Lightpath Widgets
"""
import logging
import os.path

from pydm import Display
from pydm.PyQt.QtCore import pyqtSlot
from pydm.PyQt.QtGui import QColor

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


class InactiveRow(Display):
    """
    Inactive row for happi container
    """
    def __init__(self, device, parent=None):
        super().__init__(parent=parent)
        self.device = device
        # Create labels
        self.name_label.setText(device.name)
        self.prefix_label.setText('({})'.format(device.prefix))
        # By default we mark the device as Disconnected
        self.state_label.setText('Disconnected')
        self.state_label.setStyleSheet("QLabel {color : rgb(255,0,255)}")

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
        self.device_drawing.setFixedSize(15, 15)
        self.horizontalWidget.layout().setSpacing(2)

    def expand(self):
        """Re-expand the size of the widget to show the device"""
        # Show commands and labels
        self.device_information.show()
        self.commands.show()
        # Resize drawings
        self.out_indicator.show()
        self.device_drawing.setFixedSize(50, 50)
        self.horizontalWidget.layout().setSpacing(5)


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
    def __init__(self, device, parent=None):
        super().__init__(device, parent=parent)
        # Connect up action buttons
        self.remove_button.clicked.connect(self.remove)
        self.insert_button.clicked.connect(self.insert)
        # Subscribe device to state changes
        try:
            # Wait for later to update widget
            self.device.subscribe(self.update_state,
                                  event_type=self.device.SUB_STATE,
                                  run=False)
        except Exception:
            logger.error("Widget is unable to subscribe to device %s",
                         device.name)

    @pyqtSlot()
    def remove(self):
        """
        Remove the device from the beamline
        """
        logger.info("Removing device %s ...", self.device.name)
        try:
            self.device.remove()
        except Exception as exc:
            logger.error(exc)

    @pyqtSlot()
    def insert(self):
        """Insert the device from the beamline"""
        logger.info("Inserting device %s ...", self.device.name)
        try:
            self.device.insert()
        except Exception as exc:
            logger.error(exc)

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
        self.state_label.setStyleSheet("QLabel {color: %s}" % style_color)
        self.device_drawing._default_color = color
        self.device_drawing.update()
        # Disable buttons if necessary
        self.insert_button.setEnabled((self.last_state != DeviceState.Inserted
                                       and hasattr(self.device, 'insert')))
        self.remove_button.setEnabled((self.last_state != DeviceState.Removed
                                       and hasattr(self.device, 'remove')))

    def clear_sub(self):
        """
        Clear the subscription event
        """
        self.device.clear_sub(self.update_state)
