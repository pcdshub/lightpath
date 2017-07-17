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
def server(device):
    #Setup
    server = lightpath.ui.broadcast.Broadcaster()
    server.add_device(device)
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

def test_add_device(server, device):
    #Start server
    server.run()

    pvc = client_pv('LCLS:LIGHT:VALVE')
    mps = client_pv('LCLS:LIGHT:VALVE.MPS_WARN')


    #Check proper initialization of state
    assert caget(pvc, as_string=True) == 'removed'
    assert pvc.severity == 0

    #Check proper initialization of mps
    assert caget(mps, as_string=True) == 'safe'
    #assert mps.severity == 0

    #Check syncing of state
    device.insert()
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
    time.sleep(0.5)

def test_commands(server, device):
    #Start server
    server.run()
    pvc = client_pv('LCLS:LIGHT:VALVE:CMD')
    print(server.cmds)
    #Insert the device
    pvc.put('insert')
    time.sleep(0.1)
    assert device.inserted

    #Remove the device
    pvc.put('remove')
    time.sleep(0.1)
    assert device.removed
    
    #Cleanup
    pvc.disconnect()
    del pvc
    server.cleanup()
    time.sleep(0.5)



def test_add_path(server, path):
    #Add path
    server.add_path(path)

    #Start server
    server.run()

    pvc = client_pv('LCLS:LIGHT:TST') 

    #No devices inserted
    assert caget(pvc) == 7

    #Second device inserted
    path.one.insert()
    assert caget(pvc) == 1

    #Second and fourth device inserted
    path.three.insert()
    assert caget(pvc) == 1

    #Only fourth device inserted
    path.one.remove()
    assert caget(pvc) == 3

    #Cleanup
    pvc.disconnect()
    del pvc
#    time.sleep(0.5)


