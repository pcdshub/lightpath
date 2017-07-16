############
# Standard #
############

###############
# Third Party #
###############


##########
# Module #
##########
from lightpath import LightController


def test_controller_paths(lcls):
    controller = LightController(*lcls)
    #See that we have all the beamlines accounted for
    assert all(line in controller.beamlines.keys() for line in ['HXR', 'XCS', 'MEC'])
    #We have total path lengths
    assert len(controller.xcs.devices) == 8
    assert len(controller.hxr.devices) == 10
    assert len(controller.mec.devices) == 10
    #Range of each path is correct
    assert controller.xcs.path[0]   == lcls[0]
    assert controller.xcs.path[-1]  == lcls[10]
    assert controller.hxr.path[0]   == lcls[0]
    assert controller.hxr.path[-1]  == lcls[9]
    assert controller.mec.path[0]   == lcls[0]
    assert controller.mec.path[-1]  == lcls[11]

def test_controller_device_summaries(lcls):
    controller = LightController(*lcls)

    #No impeding devices
    assert controller.destinations == []
    #Common impediment
    controller.hxr.path[0].insert()
    assert controller.destinations == [lcls[0]]
    controller.hxr.path[0].remove()
    #Use mirrors to change destination
    controller.xcs.path[-1].insert()
    controller.hxr.path[-1].insert()
    assert controller.destinations == [controller.hxr.path[-1]]
    lcls[4].insert()
    assert controller.destinations == [controller.xcs.path[-1]]
    controller.hxr.path[-1].remove()
    controller.xcs.path[-1].remove()
    lcls[4].remove()

    #No incident devices
    assert controller.incident_devices == []
    #Common incident devices
    lcls[3].insert()
    assert controller.incident_devices == [lcls[3]]
    #Multiple incident devices
    lcls[6].insert()
    assert len(controller.incident_devices) == 2
    controller.mec.path[-3].insert()
    assert len(controller.incident_devices) == 3
    controller.mec.path[-3].remove()
    lcls[6].remove()
    assert len(controller.incident_devices) == 1
    lcls[3].remove()

    #No faulted devices
    assert controller.faulted_devices == []
    #Common faulted devices
    lcls[0].insert()
    assert controller.faulted_devices == [lcls[0]]
    #Multiple faults
    controller.hxr.path[8].insert()
    assert len(controller.faulted_devices) == 2
    controller.hxr.path[2].insert()
    assert len(controller.faulted_devices) == 2


def test_path_to(lcls):
    controller = LightController(*lcls)
    bp = controller.path_to(lcls[12])
    assert len(bp.path) == 8
    assert controller.path_to(lcls[11]).path == controller.mec.path


