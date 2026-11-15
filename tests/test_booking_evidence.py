import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from bakeoff.booking_example import EXAMPLE, read_booking_example


def test_booking_evidence_is_complete_and_consistent():
    record, frozen = read_booking_example()
    assert len(frozen['cases']) == 48
    assert [lane['passed'] for lane in record['lanes']] == [48] * 5
    assert record['total_requests'] == 10
    assert record['post_hoc_cases_added'] == 0
    assert record['selected_lane'] == 'lane-2'


def test_booking_replay_works_without_packages_credentials_or_local_race(tmp_path):
    root = Path(__file__).resolve().parents[1]
    package = tmp_path / 'bakeoff'
    package.mkdir()
    for name in ('__init__.py', '__main__.py', 'config.py', 'evidence.py', 'booking_example.py'):
        shutil.copyfile(root / 'bakeoff' / name, package / name)
    shutil.copytree(EXAMPLE, tmp_path / 'examples/bookings')
    env = {k:v for k,v in os.environ.items() if k not in ('OPENAI_API_KEY','PYTHONPATH')}
    result = subprocess.run([sys.executable,'-S','-m','bakeoff','replay','--task','bookings'],
                            cwd=tmp_path,env=env,capture_output=True,text=True,timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.count('48/48') == 5
    assert not (tmp_path / 'workdir').exists()


def test_booking_archive_detects_changed_source(tmp_path):
    folder = tmp_path / 'example'
    shutil.copytree(EXAMPLE, folder)
    (folder / 'lanes/lane-2/schedule.py').write_text('# changed')
    with pytest.raises(ValueError, match='fingerprint mismatch'):
        read_booking_example(folder)
