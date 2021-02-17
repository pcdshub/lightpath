import argparse
import logging

import coloredlogs
import happi
import pydm

import lightpath
from lightpath.ui import LightApp

DEVICE_CONFIG = '/reg/g/pcds/pyps/apps/hutch-python/device_config/db.json'

logger = logging.getLogger('lightpath')


def create_arg_parser():
    parser = argparse.ArgumentParser(description='Launch the Lightpath UI')
    parser.add_argument('--db', dest='db', type=str,
                        help='Path to device configuration. {} by default'
                             ''.format(DEVICE_CONFIG))
    parser.add_argument('--version', dest='version', action='store_true',
                        help='Print the current version of the Lightpath')
    parser.add_argument('--hutches', dest='hutches', nargs='+',
                        help='Experimental Endstation to show the Lightpath')
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help='Show the DEBUG logging stream')
    return parser


def main(db, hutches):
    """
    Open the lightpath user interface for a configuration file

    Parameters
    ----------
    db: str
        Path to happi JSON database
    """
    logger.info("Launching LCLS Lightpath ...")
    # Create PyDM Application
    app = pydm.PyDMApplication(use_main_window=False)
    # Create Lightpath UI from provided database
    lc = lightpath.LightController(happi.Client(path=db),
                                   endstations=hutches)
    lp = LightApp(lc)
    # Execute
    lp.show()
    app.exec_()


def entrypoint():
    args = create_arg_parser().parse_args()
    if args.version:
        print('Lightpath Version - ', lightpath.__version__)
        return

    # Clean user input for hutches
    if args.hutches:
        hutches = [hutch.upper() for hutch in args.hutches]
    else:
        hutches = None

    # Configure logging
    level = 'DEBUG' if args.debug else 'INFO'
    coloredlogs.install(level=level, logger=logger,
                        fmt='[%(asctime)s] - %(levelname)s -  %(message)s')
    return main(args.db or DEVICE_CONFIG, hutches)
