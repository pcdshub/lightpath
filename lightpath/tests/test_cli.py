import os
from pathlib import Path
from typing import Any, Dict, List

import pydm
import pytest
from qtpy.QtWidgets import QApplication

from lightpath.main import entrypoint
from lightpath.ui import LightApp

from .conftest import cli_args


@pytest.fixture(scope='function')
def no_gui_launch(monkeypatch):

    def no_op(*args, **kwargs):
        pass

    monkeypatch.setattr(QApplication, 'exec_', no_op)
    monkeypatch.setattr(pydm.Display, 'show', no_op)


@pytest.fixture(scope='session')
def sim_cfg_path(tmp_path_factory):
    cfg_path = os.path.join(os.path.dirname(__file__), 'conf.yml')

    db_line = f'\ndb: {os.path.join(os.path.dirname(__file__), "path.json")}\n'
    # add sim db path to cfg file
    with open(cfg_path, 'r') as f_in:
        orig_conf = f_in.readlines()
        orig_conf.append(db_line)

    sim_path = tmp_path_factory.mktemp('cfg') / 'conf.yml'
    with open(sim_path, 'w') as f_out:
        f_out.write(''.join(orig_conf))

    return sim_path


@pytest.fixture(scope='function')
def launch_cli(qtbot, no_gui_launch, sim_cfg_path: Path):
    def starter(args: List[str]) -> LightApp:
        """ Launches the gui with the given args, filling cfg if needed """
        if '--cfg' in args:
            args.append(str(sim_cfg_path))

        with cli_args(args):
            lp = entrypoint()
        qtbot.addWidget(lp)
        return lp

    return starter


def test_cli_cfg(launch_cli, cfg: Dict[str, Any]):
    # smoke test
    lp = launch_cli(['lightpath', '--cfg'])

    lines = set([lp.destination_combo.itemText(i)
                 for i in range(lp.destination_combo.count())])
    assert lines == set(cfg['hutches'])
    lp.close()


def test_cli_no_args(launch_cli):
    lp = launch_cli(['lightpath', '--sim'])

    assert lp.destination_combo.count() == 9

    lp.close()


def test_cli_hutch_cfg(launch_cli, cfg: Dict[str, Any]):
    lp = launch_cli(['lightpath', '--hutches', 'XCS', '--cfg'])

    # cfg overrides hutches setting
    assert lp.destination_combo.count() == len(cfg['hutches'])
    assert lp.path.minimum_transmission == cfg['min_trans']

    lp.close()
