"""
Display the Lightpath UI with the python IOC running in the background
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############
import pydm
import qdarkstyle

##########
# Module #
##########
import lightpath.tests
from lightpath.ui import LightApp

logger = logging.getLogger('lightpath')
logging.basicConfig(level='DEBUG')


def main():
    #Gather devices
    lcls = lightpath.tests.lcls()
    [dev.insert() for dev in lcls]
    #Create Application
    app   = pydm.PyQt.QtGui.QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    #Create Lightpath
    light = LightApp(*lcls)
    light.show()
    #Execute 
    app.exec_()

if __name__ == '__main__':
    main()

