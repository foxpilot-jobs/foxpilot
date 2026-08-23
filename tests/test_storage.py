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


def test_jobs_from_multiple_sources_share_a_canonical_record(tmp_path: Path) -> None:
    with JobStore(tmp_path / "career.sqlite3") as store:
        first_id = store.upsert_job(
            {
                "source": "greenhouse",
                "source_job_id": "gh-1",
                "title": "Data Engineer",
                "company": "Example",
                "location": "Remote",
                "url": "https://greenhouse.example/gh-1",
                "description": "Build data pipelines with Python and SQL.",
            }
        )
        second_id = store.upsert_job(
            {
                "source": "company",
                "source_job_id": "company-1",
                "title": "Data Engineer",
                "company": "Example",
                "location": "Remote",
                "url": "https://example.com/jobs/data-engineer",
                "description": "Build data pipelines with Python and SQL.",
            }
        )

        assert second_id == first_id
        sources = store.get_job(first_id)["sources"]
        assert {source["source"] for source in sources} == {"company", "greenhouse"}


def test_inactive_listing_hides_canonical_job_only_when_last_source_closes(tmp_path: Path) -> None:
    with JobStore(tmp_path / "career.sqlite3") as store:
        job_id = store.upsert_job(
            {
                "source": "test",
                "source_job_id": "1",
                "title": "Data Engineer",
                "company": "Example",
                "location": "Remote",
                "description": "Build pipelines.",
            }
        )
        store.upsert_job(
            {
                "source": "mirror",
                "source_job_id": "1",
                "title": "Data Engineer",
                "company": "Example",
                "location": "Remote",
                "description": "Build pipelines.",
            }
        )
        store.mark_listing_inactive("test", "1", "HTTP 404")
        assert [job["job_id"] for job in store.list_jobs()] == [job_id]
        store.mark_listing_inactive("mirror", "1", "HTTP 410")
        assert store.list_jobs() == []
        assert store.list_jobs(include_inactive=True)[0]["is_active"] is False


def test_private_listing_is_visible_only_to_owner(tmp_path: Path) -> None:
    database = tmp_path / "career.sqlite3"
    with JobStore(database, user_id="user-a") as owner:
        job_id = owner.upsert_job(
            {
                "source": "linkedin",
                "source_job_id": "private-1",
                "title": "Staff Engineer",
                "company": "Example",
                "description": "Private imported posting.",
                "visibility": "private",
                "owner_user_id": "user-a",
            }
        )
        assert [job["job_id"] for job in owner.list_jobs()] == [job_id]

    with JobStore(database, user_id="user-b") as another_user:
        assert another_user.list_jobs() == []
        assert another_user.get_job(job_id) is None


def test_application_status_is_validated(tmp_path: Path) -> None:
    with JobStore(tmp_path / "career.sqlite3") as store:
        job_id = store.upsert_job({"source": "test", "source_job_id": "1"})
        try:
            store.save_application(job_id, "unknown")
        except ValueError as error:
            assert "Unsupported" in str(error)
        else:
            raise AssertionError("Expected invalid application status to fail")


def test_background_job_is_claimed_once(tmp_path: Path) -> None:
    database = tmp_path / "career.sqlite3"
    with JobStore(database, user_id="user-a") as store:
        store.create_background_job("job-1", "matching")
        claimed = store.claim_next_background_job()
        assert claimed is not None
        assert claimed["job_id"] == "job-1"
        assert claimed["status"] == "running"
        assert store.claim_next_background_job() is None


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
