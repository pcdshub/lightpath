from lightpath import LightController


def test_controller_paths(lcls_client):
    controller = LightController(lcls_client,
                                 endstations=['MEC', 'CXI', 'HXR', 'XCS'])
    # See that we have all the beamlines accounted for
    assert all(line in controller.beamlines.keys()
               for line in ['CXI', 'HXR', 'XCS', 'MEC'])
    # We have total path lengths
    assert len(controller.xcs.devices) == 10
    assert len(controller.hxr.devices) == 7
    assert len(controller.cxi.devices) == 10
    assert len(controller.mec.devices) == 10
    # Range of each path is correct
    assert controller.xcs.path[0].name == 'fee_valve1'
    assert controller.hxr.path[0].name == 'fee_valve1'
    assert controller.mec.path[0].name == 'fee_valve1'
    assert controller.cxi.path[0].name == 'fee_valve1'
    assert controller.xcs.path[-1].name == 's4_stopper'
    assert controller.hxr.path[-1].name == 'xrt_m2h'
    assert controller.mec.path[-1].name == 's6_stopper'
    assert controller.cxi.path[-1].name == 's5_stopper'


def test_controller_device_summaries(lcls_client):
    controller = LightController(lcls_client,
                                 endstations=['MEC', 'CXI', 'HXR', 'XCS'])

    # No impeding devices
    assert controller.destinations == []
    # Common impediment
    controller.hxr.path[0].insert()
    assert controller.destinations[0].name == 'fee_valve1'
    controller.hxr.path[0].remove()
    # Use mirrors to change destination
    controller.xcs.path[-1].insert()
    controller.cxi.path[-1].insert()
    assert controller.destinations[0].name == 's5_stopper'
    controller.hxr.path[4].insert()
    assert controller.destinations[0].name == 's4_stopper'
    controller.cxi.path[-1].remove()
    controller.xcs.path[-1].remove()
    controller.hxr.path[4].remove()

    # No incident devices
    assert controller.incident_devices == []
    # Common incident devices
    controller.hxr.path[3].insert()
    assert controller.incident_devices[0].name == 'xrt_ipm'
    # Multiple incident devices
    controller.hxr.path[6].insert()
    assert len(controller.incident_devices) == 2
    controller.mec.path[-3].insert()
    assert len(controller.incident_devices) == 3
    controller.mec.path[-3].remove()
    controller.hxr.path[6].remove()
    assert len(controller.incident_devices) == 1


def test_path_to(lcls_client):
    controller = LightController(lcls_client)
    bp = controller.path_to(controller.mec.path[-3])
    assert len(bp.path) == 8
    mec_path = controller.path_to(controller.mec.path[-1]).path
    mec_path == controller.mec.path
