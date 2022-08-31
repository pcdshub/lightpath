import argparse
import logging
from pathlib import Path

import coloredlogs
import happi
import yaml
from qtpy.QtWidgets import QApplication

import lightpath
from lightpath.ui import LightApp

logger = logging.getLogger('lightpath')
qapp = None


def create_arg_parser():
    parser = argparse.ArgumentParser(description='Launch the Lightpath UI')
    parser.add_argument('--db', dest='db', type=str,
                        help=('Path to device configuration. '
                              'Takes local happi config by default'))
    parser.add_argument('--version', dest='version', action='store_true',
                        help='Print the current version of the Lightpath')
    parser.add_argument('--sim', dest='sim', action='store_true',
                        help='Opens lightpath with a simulated LCLS facility')
    parser.add_argument('--hutches', dest='hutches', nargs='+',
                        help='Experimental endstation(s) to show in Lightpath')
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help='Show the DEBUG logging stream')
    parser.add_argument('--cfg', required=False, default=None,
                        help='Configuration yaml file')
    return parser


def get_qapp():
    """Returns the global QApplication, creating it if necessary."""
    global qapp
    if qapp is None:
        if QApplication.instance() is None:
            logger.debug("Creating QApplication ...")
            qapp = QApplication([])
        else:
            logger.debug("Using existing QApplication")
            qapp = QApplication.instance()
    return qapp


def main(db, hutches, cfg):
    """
    Open the lightpath user interface for a configuration file

    Parameters
    ----------
    db: str
        Path to happi JSON database
    """
    if cfg:
        logger.info(f'reading config from: {cfg}...')
        with open(cfg, 'r') as f:
            conf = yaml.safe_load(f)
    else:
        conf = {}

    timeout = conf.get('timeout', 10)  # timeout (s)
    from ophyd.signal import EpicsSignalBase
    EpicsSignalBase.set_defaults(timeout=timeout,
                                 connection_timeout=timeout)

    db_path = db or conf.get('db')
    if db_path:
        client = happi.Client(path=db_path)
    else:
        client = happi.Client.from_config()

    hutches = hutches or conf.get('hutches')

    logger.info("Launching LCLS Lightpath ...")
    # Create PyDM Application
    app = get_qapp()
    # Create Lightpath UI from provided database
    lc = lightpath.LightController(client, endstations=hutches, cfg=conf)
    lp = LightApp(lc)
    # Execute
    lp.show()
    app.exec_()

    return lp


def entrypoint():
    args = create_arg_parser().parse_args()
    if args.version:
        print("Lightpath Version ", lightpath.__version__)
        return

    # Clean user input for hutches
    if args.hutches:
        hutches = [hutch.upper() for hutch in args.hutches]
    else:
        hutches = None

    # set up simulated lightpath if requested
    if args.sim:
        args.db = Path(__file__).parent / 'tests' / 'path.json'

    # Configure logging
    level = 'DEBUG' if args.debug else 'INFO'
    coloredlogs.install(level=level, logger=logger,
                        fmt='[%(asctime)s] - %(levelname)s -  %(message)s')
    return main(args.db, hutches, args.cfg)
