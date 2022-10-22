from typing import Any, Dict

import happi
import pytest

from lightpath import LightController
from lightpath.errors import PathError


def test_controller_paths(lcls_client: happi.Client):
    beamlines = {'XPP': 8, 'XCS': 13, 'MFX': 14, 'CXI': 15, 'MEC': 14,
                 'TMO': 12, 'CRIX': 11, 'QRIX': 11, 'TXI': 5}

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
        assert controller.active_path(line).path[0].name == 'im1l0'
    # all SXR lines share a beginning
    for line in ['TMO', 'CRIX', 'QRIX']:
        assert controller.active_path(line).path[0].name == 'im1k0'
    # TXI omitted, doesn't work yet

    assert controller.active_path('XPP').path[-1].name == 'xpp_lodcm'
    assert controller.active_path('XCS').path[-1].name == 'im2l3'
    assert controller.active_path('MFX').path[-1].name == 'im2l5'
    assert controller.active_path('CXI').path[-1].name == 'im6l0'
    assert controller.active_path('MEC').path[-1].name == 'im2l4'
    assert controller.active_path('TMO').path[-1].name == 'sl2k4'
    assert controller.active_path('CRIX').path[-1].name == 'im4k1'
    assert controller.active_path('QRIX').path[-1].name == 'im2k2'


def test_changing_paths(lcls_ctrl: LightController):
    assert lcls_ctrl.active_path('XCS').path[-1].name == 'im2l3'
    assert lcls_ctrl.active_path('XCS').path[-3].name == 'mr1l4'
    assert (['mr1l4', 'xcs_lodcm', 'im5l0', 'sl4l0', 'im6l0'] ==
            lcls_ctrl.walk_facility()['source_L0'][-5:])

    # insert mirror to take L3 path
    lcls_ctrl.get_device('mr1l3').insert()
    assert lcls_ctrl.active_path('XCS').path[-1].name == 'im2l3'
    assert lcls_ctrl.active_path('XCS').path[-3].name == 'im1l3'
    assert (['xpp_lodcm', 'mr1l3', 'im1l3', 'sl1l3', 'im2l3'] ==
            lcls_ctrl.walk_facility()['source_L0'][-5:])

    # remove devices to prevent inter-test tampering
    lcls_ctrl.get_device('mr1l3').remove()


def test_controller_device_summaries(lcls_ctrl: LightController):
    # No impeding devices
    assert lcls_ctrl.destinations == []
    # Common impediment
    lcls_ctrl.active_path('XCS').path[1].insert()
    assert lcls_ctrl.destinations[0].name == 'sl1l0'
    lcls_ctrl.active_path('XCS').path[1].remove()
    # Use mirrors to change destination
    lcls_ctrl.get_device('mr1l4').insert()  # change from L0 -> L4
    lcls_ctrl.get_device('sl1l4').insert()
    lcls_ctrl.get_device('sl1l3').insert()
    assert lcls_ctrl.destinations[0].name == 'sl1l4'
    lcls_ctrl.get_device('mr1l3').insert()
    assert lcls_ctrl.destinations[0].name == 'sl1l3'
    lcls_ctrl.get_device('mr1l4').remove()
    lcls_ctrl.get_device('sl1l4').remove()
    lcls_ctrl.get_device('sl1l3').remove()
    lcls_ctrl.get_device('mr1l3').remove()

    # No incident devices
    assert lcls_ctrl.incident_devices == []
    # Common incident devices
    xcs_path = lcls_ctrl.active_path('XCS')
    xcs_path.path[0].insert()
    assert lcls_ctrl.incident_devices[0].name == 'im1l0'
    # Multiple incident devices
    xcs_path.path[4].insert()
    assert len(lcls_ctrl.incident_devices) == 2
    xcs_path.path[5].insert()
    assert len(lcls_ctrl.incident_devices) == 3
    xcs_path.path[5].remove()
    xcs_path.path[4].remove()
    assert len(lcls_ctrl.incident_devices) == 1
    xcs_path.path[0].remove()


def test_path_to(lcls_ctrl: LightController):
    bp = lcls_ctrl.path_to(lcls_ctrl.active_path('MEC').path[-3])
    assert len(bp.path) == 12
    mec_path = lcls_ctrl.path_to(lcls_ctrl.active_path('MEC').path[-1]).path
    mec_path == lcls_ctrl.active_path('MEC').path


def test_multi_output(lcls_ctrl: LightController):
    xcs_lodcm = lcls_ctrl.get_device('xcs_lodcm')
    assert lcls_ctrl.active_path('XCS').blocking_devices == [xcs_lodcm]
    # set lodcm to split beam
    xcs_lodcm._inserted_mode.put(1)
    xcs_lodcm.insert()

    # no impediments, both receive beam
    assert not lcls_ctrl.active_path('XCS').blocking_devices
    assert not lcls_ctrl.active_path('CXI').blocking_devices

    # set to diverge beam fully
    xcs_lodcm.remove()
    xcs_lodcm._inserted_mode.put(2)
    xcs_lodcm.insert()

    # beam goes to xcs only
    assert not lcls_ctrl.active_path('XCS').blocking_devices
    assert lcls_ctrl.active_path('CXI').blocking_devices == [xcs_lodcm]


def test_walk_facility(lcls_ctrl: LightController):
    # with all removed, expect beam straight through
    walk = lcls_ctrl.walk_facility()
    assert walk['source_L0'][-1] == 'im6l0'
    assert walk['source_K0'][-1] == 'im4k0'

    # change beam path
    lcls_ctrl.get_device('mr1k1').insert()
    lcls_ctrl.get_device('mr1l0').insert()
    walk = lcls_ctrl.walk_facility()
    assert walk['source_L0'][-1] == 'im9l1'
    assert walk['source_K0'][-1] == 'im4k1'
    assert len(walk['source_L0']) == 5
    assert len(walk['source_K0']) == 11

    # These beam paths do not represent impediments or destinations.
    # simply represents where device configurations point
    incidents = [d.name for d in lcls_ctrl.incident_devices]
    assert set(incidents) == set(['mr1l0', 'mr1k1'])
    assert len(lcls_ctrl.destinations) == 0


def test_mock_device(lcls_ctrl: LightController):
    # break some metadata
    lcls_ctrl.graph.nodes['sl1k2']['md'].res.metadata['device_class'] = ''

    # smoke test device loading
    lcls_ctrl.get_device('sl1k2')


def test_cfg_loading(lcls_client: happi.Client, cfg: Dict[str, Any]):
    # load lcls with config modifications
    lc = LightController(lcls_client, ['XCS'], cfg=cfg)

    # check modifications to default parameters
    # only loaded beamlines specified, cfg overrides endstations
    assert set(lc.beamlines.keys()) == set(cfg['hutches'])
    assert 'CRIX' not in lc.beamlines.keys()

    # min transission propogates
    assert lc.active_path('XCS').minimum_transmission == cfg['min_trans']
    assert lc.active_path('TMO').minimum_transmission == cfg['min_trans']
    assert lc.active_path('XPP').minimum_transmission == cfg['min_trans']

    # test cfg settings that don't have matching devices
    bad_cfg = {
        'beamlines': {'NOT': ['NO_BR']},
        'hutches': ['NOT']
    }
    with pytest.raises(PathError):
        bad_lc = LightController(lcls_client, cfg=bad_cfg)
        bad_lc.active_path('NOT')
