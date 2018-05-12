import io

from unittest.mock import Mock
from lightpath import BeamPath
from lightpath.path import find_device_state, DeviceState
from .conftest import Crystal, Status


def test_find_device_state(device):
    # In
    device.insert()
    assert find_device_state(device) == DeviceState.Inserted
    # Out
    device.remove()
    assert find_device_state(device) == DeviceState.Removed
    # Unknown
    device.status = Status.unknown
    assert find_device_state(device) == DeviceState.Unknown
    # Disconnected
    device.status = Status.disconnected
    # Error
    del device.status
    assert find_device_state(device) == DeviceState.Error


def test_range(path):
    assert path.range == (0., 30.)


def test_sort(path):
    for i, device in enumerate(path.path):
        try:
            # Each devices is before than the next
            assert device.md.z < path.path[i+1].md.z
        # Except for the final device
        except IndexError:
            assert i == len(path.devices) - 1


def test_branching_finding(path):
    # Find the optic along the beampath
    assert path.branches == [path.path[4]]
    assert isinstance(path.branches[0], Crystal)


def test_clear_beamline(path, branch):
    # Completely removed beamline
    assert path.blocking_devices == []
    assert not path.impediment
    assert path.cleared

    # Passive device inserted
    path.path[5].insert()
    assert path.blocking_devices == []
    assert path.incident_devices == [path.path[5]]
    assert not path.impediment
    assert path.cleared

    # Branch with optic inserted
    branch.path[4].insert()
    assert branch.blocking_devices == []
    assert branch.incident_devices == [branch.path[4]]
    assert not branch.impediment
    assert branch.cleared


def test_single_impediment(path, branch):
    # Insert generic device
    path.path[0].insert()
    assert path.impediment == path.path[0]
    assert path.blocking_devices == [path.impediment]
    assert path.incident_devices == [path.impediment]
    assert path.cleared is False
    path.path[0].remove()

    # Insert passive device
    path.path[5].insert()
    assert not path.impediment
    assert path.blocking_devices == []
    assert path.incident_devices == [path.path[5]]
    assert path.cleared is True
    path.path[5].remove()

    # Insert blocking optic
    path.path[4].insert()
    assert path.impediment == path.path[4]
    assert path.blocking_devices == [path.impediment]
    assert path.incident_devices == [path.impediment]
    assert path.cleared is False
    path.path[4].remove()

    # Removed neccesary optic
    assert branch.impediment == branch.path[4]
    assert branch.blocking_devices == [branch.impediment]
    assert branch.incident_devices == []
    assert branch.cleared is False

    # Broken device
    del path.path[0].status
    assert find_device_state(path.path[0]) == DeviceState.Error
    assert path.impediment == path.path[0]


def test_multiple_insert_beamline(path):
    # Insert two devices
    path.path[1].insert()
    path.path[3].insert()
    # Assert we have the proper stopping point
    assert path.impediment == path.path[1]
    # Assert both are accounted reported
    assert path.blocking_devices == [path.path[1], path.path[3]]
    assert path.incident_devices == [path.path[1]]


def test_show_device(path):
    # Write table to file-like object
    f = io.StringIO()
    path.show_devices(file=f)
    # Read from start of document
    f.seek(0)
    assert f.read() == known_table


def test_ignore(path):
    # Ignore only one device
    target, ignore = path._ignore(path.path[4], passive=True)
    assert ignore == [path.path[4]]
    assert path.path[4] not in target
    # Assert we are not ignoring passive devices
    assert path.path[5] in target

    # Ignore passive devices in addition
    target, ignore = path._ignore(path.path[3], passive=False)
    assert ignore == [path.path[5], path.path[3]]
    assert path.path[3] not in target
    assert path.path[5] not in target


def test_clear(path):
    # Insert a variety of devices
    path.path[0].insert()
    path.path[1].insert()
    path.path[2].insert()
    # Clear the line
    path.clear(wait=False)
    # Assert the path is clear
    assert path.cleared
    # Clear passive devices
    path.path[5].insert()
    path.clear(wait=False, passive=True)
    assert path.incident_devices == []


def test_join(path):
    # Create two partial beampaths
    first = BeamPath(*path.path[:4])
    second = BeamPath(*path.path[4:])

    # Combine in a variety of ways to same result
    assert BeamPath.from_join(first, second).path == path.path
    assert first.join(second).path == path.path
    assert second.join(first).path == path.path


def test_split(path):
    # Create two partial beampaths
    first = BeamPath(*path.path[:5])
    second = BeamPath(*path.path[5:])

    # Test split by device yields partial beampaths
    assert path.split(device=path.path[4])[0].path == first.path
    assert path.split(device=path.path[4])[1].path == second.path

    # Test split by z yields partial beampaths
    assert path.split(z=path.path[4].md.z)[0].path == first.path
    assert path.split(z=path.path[4].md.z)[1].path == second.path


def test_callback(path):
    # Create mock callback
    cb = Mock()
    # Subscribe to event changes
    path.subscribe(cb, event_type=path.SUB_PTH_CHNG, run=False)
    # Change state of beampath
    path.devices[4].insert()
    # Assert callback has been run
    assert cb.called


def test_complex_branching(lcls):
    # Upstream Optic
    xcs = [d for d in lcls if d.md.beamline in ['HXR', 'XCS']]
    bp = BeamPath(*xcs)
    # Remove all the devices
    for d in xcs:
        d.remove()
    # OffsetMirror should be blocking
    assert bp.impediment == xcs[4]
    # Insert OffsetMirror
    bp.path[4].insert()
    # Path should be cleared
    assert bp.blocking_devices == []
    # Downstream Optic
    mec = [d for d in lcls if d.md.beamline in ['HXR', 'MEC']]
    bp = BeamPath(*mec)
    # Remove all devices
    for d in mec:
        d.remove()
    # Path should be cleared
    assert bp.impediment == mec[6]
    # Insert first mirror
    bp.path[4].insert()
    assert bp.impediment == mec[4]
    # Insert second mirror
    bp.path[6].insert()
    assert bp.impediment == mec[4]
    # Retract first mirror
    bp.path[4].remove()
    assert bp.blocking_devices == []


known_table = """\
+-------+--------+----------+----------+---------+
| Name  | Prefix | Position | Beamline |   State |
+-------+--------+----------+----------+---------+
| zero  | zero   |  0.00000 |      TST | Removed |
| one   | one    |  2.00000 |      TST | Removed |
| two   | two    |  9.00000 |      TST | Removed |
| three | three  | 15.00000 |      TST | Removed |
| four  | four   | 16.00000 |      TST | Removed |
| five  | five   | 24.00000 |      TST | Removed |
| six   | six    | 30.00000 |      TST | Removed |
+-------+--------+----------+----------+---------+
"""
