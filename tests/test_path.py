import pytest


def test_start(beampath):
    assert beampath.start.z == 0.

def test_finish(beampath):
    assert beampath.finish.z == 30.
