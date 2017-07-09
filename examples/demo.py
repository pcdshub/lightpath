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
from pedl.choices import ColorChoice
##########
# Module #
##########
import lightpath.tests
from lightpath.ui import Illustrator, Broadcaster

logger = logging.getLogger(__name__)


def main():
    pth = lightpath.tests.path()

    #Create IOC
    b = Broadcaster()
    b.add_path(pth)

    #Start IOC
    b.run()

    #Create UI
    i = Illustrator()
    beam = i.draw_path(pth)
    i.app.window.setLayout(beam, resize=True)
    i.save('test.edl')

    #Launch the window
    try:
        i.show()
    #Report exception if EDM executable is not found
    except OSError as e:
        print(e)

    #Stop the IOC
    b.cleanup()


if __name__ == '__main__':
    main()

