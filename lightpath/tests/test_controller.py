import happi

from lightpath import LightController

h = happi.EntryInfo()


def test_controller_paths(lcls_client):
    beamlines = {'XPP': 15, 'XCS': 13, 'MFX': 14, 'CXI': 15, 'MEC': 14,
                 'TMO': 11, 'CRIX': 11, 'qRIX': 11, 'TXI': 5}

    # load controller with all beamlines + invalid ones
    controller = LightController(lcls_client,
                                 endstations=list(beamlines.keys()) +
                                 ['NAB', 'SIM'])
    # See that we have all the beamlines accounted for
    assert all(line in controller.beamlines.keys()
               for line in beamlines.keys())
    # We have total path lengths
    for line, length in beamlines.items():
        assert len(controller.active_path(line).devices) == length

    # Range of each path is correct
    # all HXR lines share a beginning
    for line in ['XPP', 'XCS', 'MFX', 'CXI', 'MEC']:
        assert controller.active_path(line).path[0].name == 'IM1L0:XTES'
    # all SXR lines share a beginning
    for line in ['TMO', 'CRIX', 'qRIX']:
        assert controller.active_path(line).path[0].name == 'IM1K0:XTES'
    # TXI omitted, doesn't work yet

    # XPP Shouldn't end here...
    # assert controller.active_path('XPP').path[-1].name == 'XCS:LODCM'
    assert controller.active_path('XCS').path[-1].name == 'IM2L3:PPM'
    assert controller.active_path('MFX').path[-1].name == 'IM2L5:PPM'
    assert controller.active_path('CXI').path[-1].name == 'IM6L0:XTES'
    assert controller.active_path('MEC').path[-1].name == 'IM2L4:PPM'
    assert controller.active_path('TMO').path[-1].name == 'SL2K4:SCATTER'
    assert controller.active_path('CRIX').path[-1].name == 'IM4K1:XTES'
    assert controller.active_path('qRIX').path[-1].name == 'IM2K2:PPM'


def test_controller_device_summaries(lcls_client):
    controller = LightController(lcls_client,
                                 endstations=['MEC', 'CXI', 'HXR', 'XCS'])

    # No impeding devices
    assert controller.destinations == []
    # Common impediment
    controller.active_path('XCS').path[1].insert()
    assert controller.destinations[0].name == 'SL1L0:POWER'
    controller.active_path('XCS').path[1].remove()
    # Use mirrors to change destination
    controller.get_device('mr1l4').insert()  # change from L0 -> L4
    controller.get_device('sl1l4').insert()
    controller.get_device('sl1l3').insert()
    assert controller.destinations[0].name == 'SL1L4:POWER'
    controller.get_device('mr1l3').insert()
    assert controller.destinations[0].name == 'SL1L3:POWER'
    controller.get_device('mr1l4').remove()
    controller.get_device('sl1l4').remove()
    controller.get_device('sl1l3').remove()
    controller.get_device('mr1l3').remove()

    # No incident devices
    assert controller.incident_devices == []
    # Common incident devices
    xcs_path = controller.active_path('XCS')
    xcs_path.path[0].insert()
    assert controller.incident_devices[0].name == 'IM1L0:XTES'
    # Multiple incident devices
    xcs_path.path[4].insert()
    assert len(controller.incident_devices) == 2
    xcs_path.path[5].insert()
    assert len(controller.incident_devices) == 3
    xcs_path.path[5].remove()
    xcs_path.path[4].remove()
    assert len(controller.incident_devices) == 1


def test_path_to(lcls_client):
    controller = LightController(lcls_client)
    bp = controller.path_to(controller.active_path('MEC').path[-3])
    assert len(bp.path) == 12
    mec_path = controller.path_to(controller.active_path('MEC').path[-1]).path
    mec_path == controller.active_path('MEC').path
