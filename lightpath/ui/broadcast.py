"""
The broadcast module contains the tools to report the status of the lightpath
and child devices as EPICS PVs. The instantiation of the Channel Access server
is abstracted away by the :class:`.Broadcaster` class, which can either have
devices and paths manually added with :meth:`.add_device` or
:meth:`.add_path`. If you simply wish to broadcast all the devices within a
:class:`.Controller` object, just use the classmethod :meth:`.broadcast` to
create the object. This does all the work of iterating through devices and
paths to assemble a complete IOC.

The produced Channel Access serer is  simple to understand with only four unique classes of PVs
created.

============================   ============================  =============
PV                             Purpose                       Type
============================   ============================  =============
LCLS:LIGHT:{PATH}              Location of beam along path   int
LCLS:LIGHT:{DEVICE}            State of device               enum
LCLS:LIGHT:{DEVICE}.MPS_WARN   MPS faulted, but not exposed  binary
LCLS:LIGHT:{DEVICE}.MPS_TRIP   MPS faulted and exposed       binary
LCLS:LIGHT:{DEVICE}:CMD        Command for insert/remove     binary
============================   ============================  =============

Each beamline gets a single PV that communicates where the beam is reaching
along the path. Instead of, as in past iterations of the lightpath, creating a
multitude of PVs for each stretch of beamline, this single PV is simply the
index of the first blocking device. For example, if the second device on the
beampath is inserted, the PV for that path will be equal to ``1``, because only
the zero-th and first sections of beampipe are transmitting the beam. This PV
ignores all devices that are considered passive, devices that may affect the
beam but do not prevent subsequent devices from receiving photons i.e mirrors
and attenuators.

Each device has three PVs added to the database, the first being the current
position; removed, inserted, or unknown. This simply uses the state machine
underlying each :class:`.LightDevice` to determine the state and update the
broadcast PVs as devices move along the beamline. The ``CMD`` PV exposes the
:meth:`.LightDevice.insert` and :meth:`.LightDevice.remove` methods, simply send
one of those strings, or the corresponding enums to the PV to instruct the
device to change its' state. Finally, each device has an ``MPS`` PV, but only
those with an associated :class:`.MPS` sub-device will have the PV linked to
ophyd subscription service. This allows the UI to use the same widget for each
device regardless of whether it is involved in the MPS system or not.
"""
############
# Standard #
############
import logging
from enum import Enum
###############
# Third Party #
###############
from pcaspy       import Driver, SimpleServer, Alarm, Severity
from pcaspy.tools import ServerThread

##########
# Module #
##########

prefix = 'LCLS:LIGHT:'
logger = logging.getLogger(__name__)

def convert(device, with_prefix=False):
    """
    Convert a device alias into a PV name

    Parameters
    ----------
    device : BeamPath or LightDevice
        Device to have name converted

    with_prefix : bool , optional
        Choice to append the IOC prefix

    Returns
    -------
    pv : str
        Cleaned PV name to be added to database
    """
    nm = device.name.upper().replace(' ','_')
    
    #Add prefix if neccesary
    if with_prefix:
        return prefix + nm

    return nm

class DeviceState(Enum):
    """
    Enum for translating the state machine to the PV enum
    """
    removed  = 0
    unknown  = 1
    inserted = 2

class Command(Enum):
    """
    Enum for command PV
    """
    remove = 0
    insert = 1

class Broadcaster:
    """
    Abstraction of pcaspy driver and server
    
    Attributes
    ----------
    server : ``pcaspy.Server``
    
    driver : ``pcaspy.Driver``
    
    db : dict
        Database of all PVs to be instantiated in the pcaspy server

    cmds : dict
        Mapping of each command PV to the associated device. This is given to
        the driver so that it can insert /remove the correct Python object
        based on Channel Access inputs

    subs :dict
        A database of each subscription that updates server PVs based on device
        state changes
    """
    _thread = None

    def __init__(self):
        #Database structures
        self.db   = dict()
        self.cmds = dict()
        self.subs = dict()

        #Python-IOC internals
        self.server = None
        self.driver = None


    @property
    def is_running(self):
        """
        Whether the ServerThread is actively running
        """
        if self._thread and self._thread.is_alive:
            return True

        return False


    def run(self):
        """
        Run the the internal pcaspy server
    
        If not already created, this also spawns a new ServerThread, Server and
        Driver. However, if the server has already been run, it will simply
        restart the stored copy of the server. This means that in order for the
        server to reflect any changes to the :attr:`.db`, :meth:`.cleanup`
        should be called before running again.
        """
        if self.is_running:
            print('Broadcaster is already running')
            return

        if not self._thread:
            logger.debug('Creating server for given database ...')
            #Create server
            self.server = SimpleServer()
            self.server.createPV(prefix, self.db)

            #Create driver
            self.driver = LightDriver(self.cmds)

            #Create thread
            self._thread = ServerThread(self.server)

        #Start the server
        logger.info('Starting pcaspy server ...')
        self._thread.start()

        #Update all the callbacks
        logger.debug("Running stored callbacks to update broadcast PVs")
        [cb() for cb in self.subs.keys()]


    def add_path(self, path):
        """
        Add the apppropriate PVs for a :class:`.Beampath`

        Parameters
        ----------
        path :class:`.Beampath`
            Path to be added to the server database
        """
        #Create basic PV
        pv = convert(path)

        if pv in self.db:
            raise ValueError('Path has already been added '\
                             'to the database')

        self.db[pv] = {'type' : 'int'}

        #Create syncing callback
        def sync(*args, **kwargs):
            #Find impediment
            if path.impediment:
                idx = path.devices.index(path.impediment)
            else:
                idx = len(path.devices)

            #Communicate
            self.driver.write(pv, idx)

        self.add_subscription(path, sync, event_type=path.SUB_PTH_CHNG)

        #Monitor MPS System faults
        def mps(*args, **kwargs):
            for device in [d for d in path.devices if d.mps]:
                val = int(device in path.tripped_devices)
                #Communicate
                self.driver.write(convert(device)+'.MPS_TRIP', val)

        #Create trip 
        self.add_subscription(path, mps, event_type=path.SUB_MPSPATH_CHNG)

    def add_device(self, device):
        """
        Add the appropriate PVs to the database for a :class:`.LightDevice`

        Parameters
        ----------
        device : :class:`.LightDevice`
            Device to be added to the server database
        """
        #Create pv from alias
        pv = convert(device)

        #Create basic PV
        if pv in self.db.keys():
            raise ValueError('Device already has been entered into '
                             'database')

        #Add PV structure to database
        self.db[pv] = {'type'   : 'enum',
                       'enums'  : ['removed', 'unknown', 'inserted'],
                       'states' : [Severity.NO_ALARM,
                                   Severity.MINOR_ALARM,
                                   Severity.MAJOR_ALARM]}

        def sync(*args, **kwargs):
            logger.debug('Device {} has changed state, syncing PV values'
                         ''.format(device.name))
            self.driver.write(pv, DeviceState[device.state].value)

        #Create subscription
        self.add_subscription(device, sync, event_type=device.SUB_DEV_CH)

        #Add MPS and CMD structure to database
        warn_pv = pv + '.MPS_WARN'
        trip_pv = pv + '.MPS_TRIP'
        cmd_pv  = pv + ':CMD'

        self.db[cmd_pv] = {'type'   : 'enum',
                           'enums'  : ['remove', 'insert']}

        self.db[trip_pv] = {'type'   : 'enum',
                            'value'  : 'safe',
                            'enums'  : ['safe', 'faulted'],
                            'states' : [Severity.NO_ALARM,
                                       Severity.MAJOR_ALARM]}

        self.db[warn_pv] = {'type'   : 'enum',
                            'value'  : 'safe',
                            'enums'  : ['safe', 'faulted'],
                            'states' : [Severity.NO_ALARM,
                                        Severity.MAJOR_ALARM]}

        #Register command
        self.register_cmd(cmd_pv, device)


        if device.mps:
            #Create update callback
            def mps_sync(*args, **kwargs):
                logger.debug('Device {} MPS state has changed, syncing '
                             'PV'.format(device.name))
                self.driver.write(warn_pv, int(device.mps.faulted))

            #Create subscription
            self.add_subscription(device.mps, mps_sync, event_type=device.mps.SUB_MPS)


    def add_subscription(self, device, cb, event_type=None):
        """
        Register a subscription to a LightDevice or BeamPath attribute
        
        Parameters
        ----------
        device : :class:`.LightDevice` or :class:`.Beampath`

        cb : callable
            Callable function to be run upon receiving an event

        event_type : str, optional
            Event type to create subscription. If left as None,
            it will be the default event_type of the device
        """
        device.subscribe(cb, event_type=event_type, run=False)
        self.subs[cb] = device


    def register_cmd(self, cmd, device):
        """
        Map a command to a device control PV

        Parameters
        ----------
        cmd : string
            PV name of command

        device : :class:`.LightDevice`
            Associated device to insert or remove based on received Channel
            Access data
        """
        if cmd in self.cmds:
            raise ValueError("Device mapping already exists for command.")

        self.cmds[cmd] = device


    def stop(self):
        """
        Stop the internal pcaspy server
        """
        if not self.is_running:
            print('Broadcaster is not currently running.')
            return

        logging.info("Stopping server thread from broadcasting ...")
        self._thread.stop()


    @classmethod
    def broadcast(cls, controller):
        """
        Broadcast the all the paths contained in a controller
        
        Parameters
        ----------
        controller : :class:`.Controller`
            Controller that has paths and devices

        Returns
        -------
        :class:`.Broadcaster`
            New Broadcaster with all paths and devices loaded into the database
        """
        b = cls()

        for path in controller.paths:
            b.add_path(path)

        for dev in controller.devices:
            b.add_device(dev)

        return b


    def cleanup(self):
        """
        Clean out all the internal pcaspy objects

        By deleting the associated databases and pcaspy objects, this means
        when :meth:`.run` is called again, all of this information will be
        re-processed, reflecting any added devices and paths. It is worth
        noting that this does not clear the actual pcaspy database, this needs
        to be done manually.
        """
        logger.debug('Beginning cleanup ...')
        self.stop()

        #Clear subscriptions
        for sub, dev in self.subs.items():
            dev.clear_sub(sub)

        #Clear databases
        self.subs.clear()
        self.cmds.clear()

        #Remove pcaspy internals
        self._thread = None
        self.driver  = None
        self.server  = None
        logger.info('Cleanup finished')


class LightDriver(Driver):
    """
    Reimplementation of ``pcaspy.Driver``
    
    Parameters
    ----------
    cmds : dict
        Mapping of command PVs to devices
    """
    def __init__(self, cmds):
        super(LightDriver,self).__init__()
        self.cmds = cmds


    def write(self, reason, value):
        """
        Reimplementation of ``Driver.write``

        This catches all PVs with the suffix CMD and checks if they are in the
        :attr:`.cmds` database. If they are, it makes the appropriate move
        based on the input Enum
        """
        if reason.endswith('CMD'):
            try:
                if value == Command.remove.value:
                    self.cmds[reason].remove()

                elif value == Command.insert.value:
                    self.cmds[reason].insert()

                else:
                    logger.warning('Unrecognized value for CMD')

            except KeyError:
                logger.critical('No device mapping found for {}'
                                ''.format(reason))

            except Exception as e:
                logger.warning(e)

        self.setParam(reason, value)
