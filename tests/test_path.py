import pytest


def test_start(beampath):
    assert beampath.start.z == 0.

def test_finish(beampath):
    assert beampath.finish.z == 30.

def test_range(beampath):
    assert beampath.range == (0.,30.)
