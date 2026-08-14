from pathlib import Path

from career_agent.storage import JobStore


def test_job_store_round_trip(tmp_path: Path) -> None:
    with JobStore(tmp_path / "career.sqlite3") as store:
        job = {
            "source": "test",
            "source_job_id": "1",
            "title": "Data Engineer",
            "company": "Example",
            "description": "Python",
        }
        job_id = store.upsert_job(job)
        assert store.get_job(job_id)["title"] == "Data Engineer"

        store.set_relevance(job_id, "TARGET")
        store.save_match(job_id, "hash", "ollama", "test-model", {"match_score": 90})
        assert store.list_jobs(relevance="TARGET")[0]["job_id"] == job_id
        assert store.get_match(job_id)["match"]["match_score"] == 90


def test_application_status_is_validated(tmp_path: Path) -> None:
    with JobStore(tmp_path / "career.sqlite3") as store:
        job_id = store.upsert_job({"source": "test", "source_job_id": "1"})
        try:
            store.save_application(job_id, "unknown")
        except ValueError as error:
            assert "Unsupported" in str(error)
        else:
            raise AssertionError("Expected invalid application status to fail")


def test_user_owned_state_is_isolated(tmp_path: Path) -> None:
    database = tmp_path / "career.sqlite3"
    with JobStore(database, user_id="user-a") as user_a:
        job_id = user_a.upsert_job({"source": "test", "source_job_id": "1"})
        user_a.save_match(job_id, "hash-a", "ollama", "test-model", {"score": 90})
        user_a.save_application(job_id, status="applied", notes="Private note")

    with JobStore(database, user_id="user-b") as user_b:
        assert user_b.get_match(job_id) is None
        assert user_b.get_application(job_id) is None
        assert user_b.list_matches() == []
        assert user_b.list_applications() == []

    with JobStore(database, user_id="user-a") as user_a:
        assert user_a.get_match(job_id)["match"] == {"score": 90}
        assert user_a.get_application(job_id)["notes"] == "Private note"
