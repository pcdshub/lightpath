############
# Standard #
############
import time
###############
# Third Party #
###############
import epics
import pytest
import logging

##########
# Module #
##########
import lightpath.ui.broadcast

#Hide annoying CA Exceptions
logger = logging.getLogger()
epics.ca.replace_printf_handler(fcn=logger.debug)

@pytest.fixture(scope='module')
def server():
    #Setup
    server = lightpath.ui.broadcast.Broadcaster()
    yield server
    #Catch-all
    server.cleanup()

def caget(pvc, **kwargs):
    get_value = pvc.get(with_ctrlvars=True, use_monitor=False, **kwargs)
    return get_value


def client_pv(pvname):
    pvc = epics.PV(pvname, form='time')
    pvc.wait_for_connection()
    if not pvc.connected:
        raise Exception('Failed to connect to pv %s' % pvname)

    return pvc

def test_add_device(server, mps_device):
    #Add device
    server.add_device(mps_device)

    #Start server
    server.run()

    pvc = client_pv('LCLS:LIGHT:BASIC')
    mps = client_pv('LCLS:LIGHT:BASIC.MPS')


    #Check proper initialization of state
    assert caget(pvc, as_string=True) == 'removed'
    assert pvc.severity == 0

    #Check proper initialization of mps
    assert caget(mps, as_string=True) == 'safe'
    #assert mps.severity == 0

    #Check syncing of state
    mps_device.insert()
    assert caget(pvc, as_string=True)   == 'inserted'
    assert pvc.severity == 2

    #Check syncing of mps
    assert caget(mps, as_string=True) == 'faulted'
    assert mps.severity == 2

    #Cleanup
    pvc.disconnect()
    mps.disconnect()
    del pvc
    del mps
#    time.sleep(0.5)
    server.cleanup()


def test_add_path(server, beampath):
    #Add path
    server.add_path(beampath)

    #Start server
    server.run()

    pvc = client_pv('LCLS:LIGHT:TST') 

    #No devices inserted
    assert caget(pvc) == 9

    #Second device inserted
    beampath.insert('two')
    assert caget(pvc) == 1

    #Second and fourth device inserted
    beampath.insert('three')
    assert caget(pvc) == 1

    #Only fourth device inserted
    beampath.remove('two')
    assert caget(pvc) == 3

    #Cleanup
    pvc.disconnect()
    del pvc
#    time.sleep(0.5)
    server.cleanup()

def test_commands(server, simple_device):
    #Add device
    server.add_device(simple_device)

    #Start server
    server.run()

    pvc = client_pv('LCLS:LIGHT:SIMPLE:CMD')

    #Insert the device
    pvc.put('insert')
    time.sleep(0.1)
    assert simple_device.inserted

    #Remove the device
    pvc.put('remove')
    time.sleep(0.1)
    assert simple_device.removed
    
    
    #Cleanup
    pvc.disconnect()
    del pvc
#    time.sleep(0.5)
    server.cleanup()

