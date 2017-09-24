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
from pydm import Display
from pydm.PyQt.QtCore     import pyqtSlot, Qt
from pydm.PyQt.QtGui      import QSizePolicy
from pydm.widgets.drawing import PyDMDrawingRectangle

##########
# Module #
##########

logger = logging.getLogger(__name__)

class LightRow(Display):
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
    def __init__(self, device, path, parent=None):
        super().__init__(parent=parent)
        self.device = device
        self.path   = path
        #Create labels 
        self.name_label.setText(device.name)
        self.prefix_label.setText('({})'.format(device.prefix))
        #Connect button to slot
        self.remove_button.clicked.connect(self.remove)
        #Create Beam Indicator
        self.indicator = PyDMDrawingRectangle()
        self.indicator.setMinimumSize(40, 20)
        self.indicator.setSizePolicy(QSizePolicy.Fixed,
                                     QSizePolicy.Expanding)
        self.widget_layout.insertWidget(0, self.indicator)
        #Run once for correct state initialization
        self.update_state()
        self.update_mps()
        self.update_path()
        #Subscribe device to state changes
        self.path.subscribe(self.update_path, run=False)
        self.device.subscribe(self.update_state, run=False)
        self.path.subscribe(self.update_mps,
                            event_type=path.SUB_MPSPATH_CHNG,
                            run=False)

    def update_path(self, *args,  **kwargs):
        """
        Update the PyDMRectangle to show the device as in the beam or not
        """
        #If our device is before or at the impediment, it is lit
        if not self.path.impediment or (self.device.z
                                        <= self.path.impediment.z):
            self.indicator._default_color = Qt.cyan
        #Otherwise, it is off
        else:
            self.indicator._default_color = Qt.gray
        #Update widget display
        self.indicator.update()

    def update_mps(self, *args, **kwargs):
        """
        Update the MPS status of the frame

        The frame of the row will be red if the device is tripping the beam,
        yellow if it is faulted but a full trip is being prevented by an
        upstream device
        """
        if self.device in self.path.tripped_devices:
            self.frame.setStyleSheet("#frame {border: 2px solid red}")

        elif self.device in self.path.faulted_devices:
            self.frame.setStyleSheet("#frame {border: 2px solid \
                                                         rgb(255,215,0)}")
        else:
            self.frame.setStyleSheet("#frame {border: 2px solid black}")

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
            self.state_label.setStyleSheet("QLabel {color : rgb(124, 252,0)}")
        else:
            self.state_label.setStyleSheet("QLabel {color : red}")
        #Disable the button
        self.remove_button.setEnabled(state!=states.Removed.value)

    @pyqtSlot()
    def remove(self):
        """
        Remove the device from the beamline
        """
        logger.info("Removing device %s ...", self.device.name)
        try:
            self.device.remove(wait=False)
        except Exception as exc:
            logger.error(exc)

    def ui_filename(self):
        """
        Name of designer UI file
        """
        return 'lightrow.ui'

    def ui_filepath(self):
        """
        Full path to :attr:`.ui_filename`
        """
        return path.join(path.dirname(path.realpath(__file__)),
                         self.ui_filename())

    def clear_sub(self):
        """
        Clear the subscription event
        """
        self.device.clear_sub(self.update_state)
        self.path.clear_sub(self.update_mps)
        self.path.clear_sub(self.update_path)
