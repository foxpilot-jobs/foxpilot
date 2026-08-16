import sqlite3
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


def test_legacy_user_owned_tables_are_upgraded(tmp_path: Path) -> None:
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE jobs (
                job_id VARCHAR PRIMARY KEY,
                source VARCHAR NOT NULL,
                source_job_id VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                company VARCHAR NOT NULL,
                location VARCHAR NOT NULL,
                url VARCHAR NOT NULL,
                description TEXT NOT NULL,
                first_published VARCHAR,
                work_type VARCHAR,
                payload_json JSON NOT NULL,
                local_relevance VARCHAR,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );
            CREATE TABLE matches (
                job_id VARCHAR PRIMARY KEY,
                job_hash VARCHAR NOT NULL,
                provider VARCHAR NOT NULL,
                model VARCHAR NOT NULL,
                result_json JSON NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );
            CREATE TABLE applications (
                job_id VARCHAR PRIMARY KEY,
                status VARCHAR NOT NULL,
                notes TEXT NOT NULL,
                applied_at DATETIME,
                updated_at DATETIME NOT NULL
            );
            INSERT INTO jobs VALUES
              ('job-1', 'test', '1', 'Data Engineer', 'Example', '', '', '', '', '',
               '{"job_id":"job-1","title":"Data Engineer"}', NULL,
               CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            INSERT INTO matches VALUES
              ('job-1', 'hash', 'ollama', 'test-model', '{"score":90}',
               CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            INSERT INTO applications VALUES
              ('job-1', 'saved', '', NULL, CURRENT_TIMESTAMP);
            """
        )

    with JobStore(database, user_id="local-user") as local:
        assert local.get_match("job-1")["match"] == {"score": 90}
        assert local.get_application("job-1")["status"] == "saved"
        local.save_match("job-1", "new-hash", "ollama", "test-model", {"score": 95})

    with JobStore(database, user_id="another-user") as another_user:
        assert another_user.get_match("job-1") is None
        another_user.save_match("job-1", "hash", "ollama", "test-model", {"score": 80})
        assert another_user.get_match("job-1")["match"] == {"score": 80}
