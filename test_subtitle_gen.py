"""Smoke test for the pure-logic pieces of subtitle_gen - no ffmpeg/whisper
needed. Run with: python test_subtitle_gen.py"""

import os
import tempfile

from subtitle_gen.workspace import format_ts, hash_path, JobWorkspace


def test_format_ts():
    assert format_ts(0) == "00:00:00,000"
    assert format_ts(61.5) == "00:01:01,500"
    assert format_ts(3661.5) == "01:01:01,500"


def test_hash_path_stable():
    assert hash_path("a/b/c.mp4") == hash_path("a/b/c.mp4")
    assert hash_path("a/b/c.mp4") != hash_path("a/b/d.mp4")


def test_job_workspace_chunk_paths_zero_padded():
    with tempfile.TemporaryDirectory() as work_root:
        ws = JobWorkspace(work_root, "some/video.webm")
        assert ws.chunk_video_path(0).endswith("chunk_0000.mkv")
        assert ws.chunk_video_path(42).endswith("chunk_0042.mkv")


def test_job_workspace_resume_index_with_no_prior_run():
    with tempfile.TemporaryDirectory() as work_root:
        ws = JobWorkspace(work_root, "some/video.webm")
        assert ws.existing_subtitle_index() == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")
