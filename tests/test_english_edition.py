"""English messages and integrity checks must remain effective after localization."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from scripts import wmlab_verify

ROOT = Path(__file__).resolve().parents[1]


def test_localized_toolkit_is_verified_and_disclosed():
    result = wmlab_verify.verify_vendor()
    assert result['localized_toolkit_hashes_verified'] is True
    assert result['original_toolkit_unchanged'] is False
    assert result['version'] == '0.1.1'


@pytest.mark.parametrize('target', [
    'vendor/starter_kit/wmlab/wmlab/checks.py',
    'vendor/STARTER_KIT_PROVENANCE.json',
])
def test_localization_does_not_disable_integrity_checks(tmp_path, monkeypatch, target):
    shutil.copytree(ROOT/'vendor', tmp_path/'vendor',
                    ignore=shutil.ignore_patterns('build', '*.egg-info', '__pycache__'))
    file = tmp_path/target
    file.write_bytes(file.read_bytes()+b'\n')
    monkeypatch.setattr(wmlab_verify, 'ROOT', tmp_path)
    with pytest.raises(RuntimeError, match='modified|recorded hash'):
        wmlab_verify.verify_vendor()


def test_wrong_active_toolkit_is_rejected(tmp_path, monkeypatch):
    source = Path(wmlab_verify.wmlab.__file__).parent
    shutil.copytree(source, tmp_path/'wmlab', ignore=shutil.ignore_patterns('__pycache__'))
    file = tmp_path/'wmlab/checks.py'
    file.write_bytes(file.read_bytes()+b'\n')
    monkeypatch.setattr(wmlab_verify.wmlab, '__file__', str(tmp_path/'wmlab/__init__.py'))
    with pytest.raises(RuntimeError, match='Active wmlab differs'):
        wmlab_verify.verify_vendor()


@pytest.mark.parametrize('language', ['en', 'vi'])
def test_toolkit_legacy_language_selector_still_produces_english(tmp_path, language):
    scenario = tmp_path/'invalid.yaml'
    scenario.write_text('{}\n', encoding='utf-8')
    run = subprocess.run([sys.executable, '-m', 'wmlab', 'validate', str(scenario)],
                         env={**os.environ, 'WMLAB_LANG': language},
                         capture_output=True, text=True, cwd=ROOT)
    assert run.returncode != 0
    assert 'INVALID:' in run.stdout
    assert 'missing required field' in run.stdout
