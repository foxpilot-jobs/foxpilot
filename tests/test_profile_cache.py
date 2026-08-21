import json
from pathlib import Path

from career_agent.config import AppConfig
from career_agent.profile import has_current_local_profile, resume_fingerprint


def test_local_profile_cache_tracks_resume_path_and_content(tmp_path: Path) -> None:
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"resume-v1")
    config = AppConfig(data_dir=tmp_path, resume_path=resume)
    config.profile_path.write_text("{}", encoding="utf-8")
    config.profile_metadata_path.write_text(
        json.dumps({"resume_path": str(resume), "resume_sha256": resume_fingerprint(resume)}),
        encoding="utf-8",
    )

    assert has_current_local_profile(config)

    resume.write_bytes(b"resume-v2")
    assert not has_current_local_profile(config)
