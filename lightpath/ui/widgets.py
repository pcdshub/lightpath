"""
Definitions for Lightpath Widgets
"""
############
# Standard #
############
import logging
from enum import Enum
from os   import path

###############
# Third Party #
###############
from pydm.PyQt.QtCore     import pyqtSlot, Qt
from pydm.PyQt.QtGui      import QSizePolicy
from pydm.PyQt.QtGui      import QHBoxLayout, QWidget, QGridLayout, QLabel
from pydm.PyQt.QtGui      import QFont, QFrame, QSpacerItem, QPushButton
from pydm.widgets.drawing import PyDMDrawingRectangle

##########
# Module #
##########

logger = logging.getLogger(__name__)


class InactiveRow:
    """
    Inactive row for happi container
    """
    font = QFont()
    font.setPointSize(14)
    #Italic
    italic = QFont()
    font.setPointSize(12)
    italic.setItalic(True)
    #Bold
    bold = QFont()
    bold.setBold(True)

    def __init__(self, device, parent=None):
        self.device = device
        #Create labels 
        self.name_label = QLabel(parent=parent)
        self.name_label.setText(device.name)
        self.name_label.setFont(self.bold)
        self.prefix_label = QLabel(parent=parent)
        self.prefix_label.setObjectName('prefix_frame')
        self.prefix_label.setText('({})'.format(device.prefix))
        self.prefix_label.setFont(self.italic)
        self.state_label = QLabel('Disconnected',parent=parent)
        self.state_label.setFont(self.bold)
        self.state_label.setStyleSheet("QLabel {color : rgb(255,0,255)}")
        #Create Beam Indicator
        self.indicator = PyDMDrawingRectangle(parent=parent)
        self.indicator.setMinimumSize(40, 20)
        self.indicator.setSizePolicy(QSizePolicy.Fixed,
                                     QSizePolicy.Expanding)
        #Spacer
        self.spacer = QSpacerItem(40, 20)
        #Store framing for MPS updates
        self.frame_layout = QHBoxLayout()
        self.frame_layout.addWidget(self.name_label)
        self.frame = QFrame(parent=parent)
        self.frame.setObjectName('name_frame')
        self.frame.setLayout(self.frame_layout)

    @property
    def widgets(self):
        """
        Ordered list of widgets to add to designer
        """
        return [self.indicator,
                self.frame,
                self.prefix_label,
                self.spacer,
                self.state_label]

    def clear_sub(self):
        """
        Implemented by rows that have subscriptions
        """
        pass


class LightRow(InactiveRow):
    """
    Basic Widget to display LightDevice information

    The widget shows the device information and state, updating looking at the
    devices :attr:`.inserted` and :attr:`.removed` attributes. The
    :attr:`.remove_button` also allows the user to remove devices by calling
    the :meth:`.remove` method of the given device. Finally, PyDMRectangle is
    used to show the current path of the beam through the table

    Parameters
    ----------
    device : obj

    path : BeamPath

    parent : QObject, optional
    """
    def __init__(self, device, parent=None):
        super().__init__(device, parent=parent)
        #Create PushButton
        self.remove_button = QPushButton('Remove', parent=parent)
        self.remove_button.setFont(self.font)
        #Subscribe device to state changes
        try:
            #Wait for later to update widget
            self.device.subscribe(self.update_state,
                                  event_type=self.device.SUB_STATE,
                                  run=False)
        except:
            logger.error("Widget is unable to subscribe to device %s",
                         device.name)

    def update_state(self, *args, **kwargs):
        """
        Update the state label

        The displayed state can be one of ``Unknown`` , ``Inserted``,
        ``Removed`` or ``Error``, with ``Unknown`` being if the device is not
        inserted or removed, and error being if the device is reporting as both
        inserted and removed. The color of the label is also adjusted to either
        green or red to quickly 
        """
        states = Enum('states', ('Unknown', 'Inserted', 'Removed', 'Error'))
        #Interpret state
        try:
            state  = 1 + int(self.device.inserted) + 2*int(self.device.removed)
        except Exception as exc:
            logger.error(exc)
            state = states.Error.value
        #Set label to state description
        self.state_label.setText(states(state).name)
        #Set the color of the label
        if state == states.Removed.value:
            self.state_label.setStyleSheet("QLabel {color : rgb(124,252,0)}")
        elif state == states.Unknown.value:
            self.state_label.setStyleSheet("QLabel {color : rgb(255, 215, 0)}")
        else:
            self.state_label.setStyleSheet("QLabel {color : red}")
        #Disable the button
        self.remove_button.setEnabled(state!=states.Removed.value)

    @property
    def widgets(self):
        """
        Ordered list of widgets to add to designer
        """
        return [self.indicator,
                self.frame,
                self.prefix_label,
                self.spacer,
                self.state_label,
                self.remove_button]

    @pyqtSlot(bool)
    def remove(self, value):
        """
        Remove the device from the beamline
        """
        logger.info("Removing device %s ...", self.device.name)
        try:
            self.device.remove(wait=False)
        except Exception as exc:
            logger.error(exc)

    def clear_sub(self):
        """
        Clear the subscription event
        """
        self.device.clear_sub(self.update_state)
