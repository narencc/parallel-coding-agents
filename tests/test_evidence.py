"""Public example integrity and credential-free replay checks; no paid requests."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from bakeoff.evidence import EXAMPLE, read_example, replay


def test_published_example_matches_every_observation_and_cost():
    record = read_example()
    assert [l['original_passed'] for l in record['lanes']] == [44] * 5
    assert [l['review_passed'] for l in record['lanes']] == [22, 22, 22, 17, 17]
    assert record['total_requests'] == 13
    assert record['selected_lane'] == 'lane-1'


def test_replay_works_in_fresh_copy_without_packages_key_or_workdir(tmp_path):
    root = Path(__file__).resolve().parents[1]
    package = tmp_path / 'bakeoff'
    package.mkdir()
    for name in ('__init__.py', '__main__.py', 'config.py', 'evidence.py'):
        shutil.copyfile(root / 'bakeoff' / name, package / name)
    shutil.copytree(EXAMPLE, tmp_path / 'examples/money-converter')
    env = {k: v for k, v in os.environ.items() if k not in ('OPENAI_API_KEY', 'PYTHONPATH')}
    result = subprocess.run([sys.executable, '-S', '-m', 'bakeoff', 'replay', '--lane', 'lane-3'],
                            cwd=tmp_path, env=env, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert 'RECORDED-RUN REPLAY' in result.stdout
    assert 'Draft 2' in result.stdout
    assert not (tmp_path / 'workdir').exists()


def test_replay_does_not_import_candidates_or_credentials(monkeypatch, capsys):
    import builtins
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if any(x in name for x in ('money', 'credentials', 'openai', 'dotenv')):
            raise AssertionError('Replay must only read records')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    assert replay() == 0
    assert '17/22' in capsys.readouterr().out


def test_tampered_candidate_is_rejected(tmp_path):
    folder = tmp_path / 'example'
    shutil.copytree(EXAMPLE, folder)
    (folder / 'lanes/lane-1/money.py').write_text('# changed')
    with pytest.raises(ValueError, match='fingerprint mismatch'):
        read_example(folder)


def test_summary_cannot_disagree_with_cases_even_if_manifest_is_updated(tmp_path):
    folder = tmp_path / 'example'
    shutil.copytree(EXAMPLE, folder)
    data = json.loads((folder / 'run.json').read_text())
    data['lanes'][3]['review_passed'] = 22
    (folder / 'run.json').write_text(json.dumps(data))
    manifest = json.loads((folder / 'manifest.json').read_text())
    manifest['run.json'] = hashlib.sha256((folder / 'run.json').read_bytes()).hexdigest()
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='Summary differs'):
        read_example(folder)


def test_manifest_cannot_reference_outside_example(tmp_path):
    folder = tmp_path / 'example'
    shutil.copytree(EXAMPLE, folder)
    (folder / 'manifest.json').write_text(json.dumps({'../private': 'fake'}))
    with pytest.raises(ValueError, match='Unsafe example path'):
        read_example(folder)


def test_unknown_lane_returns_a_helpful_failure(capsys):
    assert replay('lane-9') == 1
    assert 'lane-1 through lane-5' in capsys.readouterr().out
