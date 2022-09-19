import logging
import os.path
import sys
from contextlib import contextmanager

import happi
import pytest
import yaml

from lightpath import BeamPath
from lightpath.controller import LightController
from lightpath.mock_devices import (IPIMB, LODCM, Crystal, Stopper,  # noqa
                                    Valve)


#################
# Logging Setup #
#################
# Enable the logging level to be set from the command line
def pytest_addoption(parser):
    parser.addoption("--log", action="store", default="DEBUG",
                     help="Set the level of the log")
    parser.addoption("--logfile", action="store", default='log',
                     help="Write the log output to specified file path")


# Create a fixture to automatically instantiate logging setup
@pytest.fixture(scope='session', autouse=True)
def set_level(pytestconfig):
    # Read user input logging level
    log_level = getattr(logging, pytestconfig.getoption('--log'), None)

    # Report invalid logging level
    if not isinstance(log_level, int):
        raise ValueError("Invalid log level : {}".format(log_level))

    # Create basic configuration
    logging.basicConfig(level=log_level,
                        filename=pytestconfig.getoption('--logfile'))


############
# Fixtures #
############
# Basic Device
@pytest.fixture(scope='function')
def device():
    return Valve('valve', name='valve', z=40.0, input_branches=['TST'],
                 output_branches=['TST'])


# Basic Beamline
def simulated_path():
    # Assemble device lists
    devices = [Valve('zero', name='zero', z=0., input_branches=['TST'],
                     output_branches=['TST']),
               Valve('one', name='one', z=2., input_branches=['TST'],
                     output_branches=['TST']),
               Stopper('two', name='two', z=9., input_branches=['TST'],
                       output_branches=['TST']),
               Valve('three', name='three', z=15., input_branches=['TST'],
                     output_branches=['TST']),
               Crystal('four', name='four', z=16., input_branches=['TST'],
                       output_branches=['TST', 'SIM']),
               IPIMB('five', name='five', z=24., input_branches=['TST'],
                     output_branches=['TST']),
               IPIMB('six', name='six', z=24.2, input_branches=['TST'],
                     output_branches=['TST']),
               IPIMB('seven', name='seven', z=24.4, input_branches=['TST'],
                     output_branches=['TST']),
               IPIMB('eight', name='eight', z=24.6, input_branches=['TST'],
                     output_branches=['TST']),
               IPIMB('nine', name='nine', z=24.8, input_branches=['TST'],
                     output_branches=['TST']),
               Valve('ten', name='ten', z=30., input_branches=['TST'],
                     output_branches=['TST'])
               ]
    # Create semi-random order
    devices = sorted(devices, key=lambda d: d.prefix)
    # Create beampath
    return BeamPath(*devices, name='TST')


@pytest.fixture(scope='function')
def path():
    return simulated_path()


# Beamline that requires optic insertion
@pytest.fixture(scope='function')
def branch():
    # Assemble device lists
    devices = [Valve('zero', name='zero', z=0., input_branches=['TST'],
                     output_branches=['TST']),
               Valve('one', name='one', z=2., input_branches=['TST'],
                     output_branches=['TST']),
               Stopper('two', name='two', z=9., input_branches=['TST'],
                       output_branches=['TST']),
               Valve('three', name='three', z=15., input_branches=['TST'],
                     output_branches=['TST']),
               Crystal('four', name='four', z=16., input_branches=['TST'],
                       output_branches=['TST', 'SIM']),
               IPIMB('five', name='five', z=24., input_branches=['SIM'],
                     output_branches=['SIM']),
               Valve('six', name='six', z=30., input_branches=['SIM'],
                     output_branches=['SIM'])]
    # Create semi-random order
    devices = sorted(devices, key=lambda d: d.prefix)
    # Create beampath
    return BeamPath(*devices, name='SIM')


# Simplified LCLS layout
@pytest.fixture(scope='function')
def lcls():
    return [Valve('FEE Valve 1', name='fee_val1', z=0., input_branches=['L0'],
                  output_branches=['L0']),
            Valve('FEE Valve 2', name='fee_val2', z=2., input_branches=['L0'],
                  output_branches=['L0']),
            Stopper('S2 Stopper', name='s2_st', z=9., input_branches=['L0'],
                    output_branches=['L0']),
            IPIMB('XRT IPM', name='xrt_ipm', z=15., input_branches=['L0'],
                  output_branches=['L0']),
            Crystal('XRT M1H', name='xrt_m1h', z=16., input_branches=['L0'],
                    output_branches=['L0', 'L3']),
            Valve('XRT Valve', name='xrt_valve', z=18., input_branches=['L0'],
                  output_branches=['L0']),
            Crystal('XRT M2H', name='xrt_m2h', z=20., input_branches=['L0'],
                    output_branches=['L0', 'L4']),
            IPIMB('HXR IPM', name='hxr_ipm', z=24., input_branches=['L0'],
                  output_branches=['L0']),
            Valve('HXR Valve', name='hxr_valve', z=25., input_branches=['L0'],
                  output_branches=['L0']),
            Stopper('S5 Stopper', name='s5_st', z=31., input_branches=['L0'],
                    output_branches=['L0']),
            Stopper('S4 Stopper', name='s4_st', z=32., input_branches=['L3'],
                    output_branches=['L3']),
            Stopper('S6 Stopper', name='s6_st', z=30., input_branches=['L4'],
                    output_branches=['L4']),
            IPIMB('MEC IPM', name='mec_ipm', z=24., input_branches=['L4'],
                  output_branches=['L4']),
            Valve('MEC Valve', name='mec_valve', z=25., input_branches=['L4'],
                  output_branches=['L4']),
            IPIMB('XCS IPM', name='xcs_ipm', z=21., input_branches=['L3'],
                  output_branches=['L3']),
            Valve('XCS Valve', name='xcs_valve', z=22., input_branches=['L3'],
                  output_branches=['L3'])]


@pytest.fixture(scope='function')
def lcls_client(monkeypatch):
    db = os.path.join(os.path.dirname(__file__), 'path.json')
    print(db)
    client = happi.Client(path=db)

    # monkeypatch to never use cache to get device
    # cached devices will retain callback information between tests
    old_get = happi.SearchResult.get

    def new_get(self, use_cache=True, **kwargs):
        return old_get(self, use_cache=False, **kwargs)

    monkeypatch.setattr(happi.SearchResult, 'get', new_get)
    return client


def simulated_lcls():
    """ LightController with simulated lcls facility for testing """
    db = os.path.join(os.path.dirname(__file__), 'path.json')
    client = happi.Client(path=db)

    return LightController(client)


@pytest.fixture(scope='function')
def lcls_ctrl(lcls_client: happi.Client):
    print(f'first item: {lcls_client.search()[0]}')
    return LightController(lcls_client)


@pytest.fixture(scope='function')
def cfg():
    cfg_path = os.path.join(os.path.dirname(__file__), 'conf.yml')
    with open(cfg_path, 'r') as f:
        cfg = yaml.safe_load(f)

    return cfg


@contextmanager
def cli_args(args):
    """
    Context manager for running a block of code with a specific set of
    command-line arguments.
    """
    prev_args = sys.argv
    sys.argv = args
    yield
    sys.argv = prev_args
