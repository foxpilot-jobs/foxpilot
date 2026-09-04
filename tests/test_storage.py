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
        assert store.list_jobs(relevance="TARGET")["items"][0]["job_id"] == job_id
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
        canonical = store.get_job(first_id)
        sources = canonical["sources"]
        assert {source["source"] for source in sources} == {"company", "greenhouse"}
        assert canonical["active_listing_count"] == 2
        assert canonical["normalized_company"] == "example"
        assert canonical["normalized_location"] == "remote"
        assert canonical["canonical_content_hash"]

        store.upsert_job(
            {
                "source": "greenhouse",
                "source_job_id": "gh-1",
                "title": "Data Engineer",
                "company": "Example",
                "location": "Remote",
                "url": "https://greenhouse.example/roles/gh-1",
                "description": "Build data pipelines with Python and SQL.",
            }
        )
        greenhouse = next(
            source
            for source in store.get_job(first_id)["sources"]
            if source["source"] == "greenhouse"
        )
        assert greenhouse["url"] == "https://greenhouse.example/roles/gh-1"
        assert greenhouse["source_url_history"] == ["https://greenhouse.example/gh-1"]


def test_inactive_listing_hides_canonical_job_only_when_last_source_closes(
    tmp_path: Path,
) -> None:
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
        assert [job["job_id"] for job in store.list_jobs()["items"]] == [job_id]
        store.mark_listing_inactive("mirror", "1", "HTTP 410")
        assert store.list_jobs()["items"] == []
        assert store.list_jobs(include_inactive=True)["items"][0]["is_active"] is False


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
        assert [job["job_id"] for job in owner.list_jobs()["items"]] == [job_id]

    with JobStore(database, user_id="user-b") as another_user:
        assert another_user.list_jobs()["items"] == []
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
        assert user_b.list_matches()["items"] == []
        assert user_b.list_applications()["items"] == []

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


def test_list_jobs_bulk_query_does_not_n_plus_one(tmp_path: Path) -> None:
    database = tmp_path / "bulk_jobs.sqlite3"
    with JobStore(database) as store:
        for i in range(10):
            store.upsert_job(
                {
                    "source": f"source_{i}",
                    "source_job_id": f"job_{i}",
                    "title": f"Engineer {i}",
                    "company": "Tech Corp",
                }
            )

        executed_statements = []

        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            executed_statements.append(statement)

        from sqlalchemy import event

        event.listen(store.engine, "before_cursor_execute", before_cursor_execute)
        try:
            result = store.list_jobs()
            assert len(result["items"]) == 10
            # Expect exactly 3 SQL statements: 1 for count, 1 for jobs, 1 for job_listings.
            assert len(executed_statements) == 3
        finally:
            event.remove(store.engine, "before_cursor_execute", before_cursor_execute)


def test_get_session_user_last_seen_touch_threshold(tmp_path: Path) -> None:
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    database = tmp_path / "session_test.sqlite3"
    with JobStore(database) as store:
        store.create_user("u1", "u1@example.com", "hash")
        token_hash = "token_hash_123"
        expires_at = datetime.now(UTC) + timedelta(days=1)
        store.create_session(str(uuid4()), "u1", token_hash, expires_at)

        # Second call within threshold (5m) skips touch write transaction
        user_second = store.get_session_user(token_hash)
        assert user_second is not None
        assert user_second["email"] == "u1@example.com"


def test_bulk_upsert_jobs_preserves_uniqueness_and_canonical_deduplication(
    tmp_path: Path,
) -> None:
    database = tmp_path / "bulk_test.sqlite3"
    with JobStore(database) as store:
        batch_1 = [
            {
                "source": "source1",
                "source_job_id": "101",
                "title": "Backend Engineer",
                "company": "Acme Corp",
                "location": "Remote",
                "description": "Building scalable Python APIs and PostgreSQL databases.",
            },
            {
                "source": "source1",
                "source_job_id": "102",
                "title": "Frontend Engineer",
                "company": "Acme Corp",
                "location": "Remote",
                "description": "Building modern React interfaces with Tailwind.",
            },
        ]
        res1 = store.bulk_upsert_jobs(batch_1)
        assert res1["inserted"] == 2
        assert res1["updated"] == 0
        assert res1["deduplicated"] == 0

        # Batch 2: Update job 101, add duplicate job 101 from source2 (canonical match)
        batch_2 = [
            {
                "source": "source1",
                "source_job_id": "101",
                "title": "Backend Engineer",
                "company": "Acme Corp",
                "location": "Remote",
                "description": "Building scalable Python APIs and PostgreSQL databases.",
            },
            {
                "source": "source2",
                "source_job_id": "999",
                "title": "Backend Engineer",
                "company": "Acme Corp",
                "location": "Remote",
                "description": "Building scalable Python APIs and PostgreSQL databases.",
            },
        ]
        res2 = store.bulk_upsert_jobs(batch_2)
        assert res2["updated"] == 1
        assert res2["deduplicated"] == 1

        # Verify database state
        all_jobs = store.list_jobs()["items"]
        assert len(all_jobs) == 2
        be_job = next(j for j in all_jobs if j["title"] == "Backend Engineer")
        assert len(be_job["sources"]) == 2


def test_workspace_lifecycle(tmp_path: Path) -> None:
    """Create, switch, rename, and delete workspaces; verify profile isolation."""
    db = tmp_path / "ws.sqlite3"
    with JobStore(db, user_id="alice") as store:
        # Default workspace auto-created on first save_profile
        store.save_profile("Resume text A", "resume_a.pdf", {"name": "Alice A"})
        ws_list = store.list_workspaces()
        assert len(ws_list) == 1
        assert ws_list[0]["is_active"] is True
        default_id = ws_list[0]["workspace_id"]

        # Create a second workspace and verify it is not yet active
        ws2 = store.create_workspace("PM pivot")
        assert not ws2["is_active"]
        assert len(store.list_workspaces()) == 2

        # Rename the second workspace
        renamed = store.rename_workspace(ws2["workspace_id"], "Product roles")
        assert renamed is True
        assert store.list_workspaces()[1]["name"] == "Product roles"

        # Switch to the second workspace; profile should be empty there
        switched = store.switch_workspace(ws2["workspace_id"])
        assert switched is True
        assert store.get_profile() is None

        # Save a new profile in the second workspace
        store.save_profile("Resume text B", "resume_b.pdf", {"name": "Alice B"})
        profile_b = store.get_profile()
        assert profile_b is not None
        assert profile_b["profile_json"]["name"] == "Alice B"

        # Switch back; should see original profile
        store.switch_workspace(default_id)
        assert store.get_profile()["profile_json"]["name"] == "Alice A"
        profile_a = store.get_profile()
        assert profile_a is not None
        assert profile_a["profile_json"]["name"] == "Alice A"

        # delete_resume only clears the file, not the extracted profile
        store.delete_resume()
        after_resume_delete = store.get_profile()
        assert after_resume_delete is not None
        assert after_resume_delete["resume_text"] == ""
        assert after_resume_delete["profile_json"]["name"] == "Alice A"

        # delete_profile scrubs both
        store.delete_profile()
        assert store.get_profile() is None

        # Deleting the only remaining workspace with data is allowed if another exists
        deleted = store.delete_workspace(ws2["workspace_id"])
        assert deleted is True
        assert len(store.list_workspaces()) == 1
        assert store.list_workspaces()[0]["workspace_id"] == default_id
        assert store.list_workspaces()[0]["is_active"] is True


def test_save_profile_reactivates_default_workspace_when_inactive(tmp_path: Path) -> None:
    """Regression test for save_profile when default workspace exists with is_active=False."""
    db = tmp_path / "ws_reactivate.sqlite3"

    # 1. New user: save_profile creates active default workspace
    with JobStore(db, user_id="bob") as store:
        store.save_profile("Resume 1", "r1.pdf", {"skills": ["Python"]})
        ws_list = store.list_workspaces()
        assert len(ws_list) == 1
        assert ws_list[0]["is_active"] is True
        default_id = ws_list[0]["workspace_id"]
        assert default_id == "ws_default_bob"

        # 2. Existing user with active default workspace -> save_profile updates existing
        store.save_profile("Resume 1 updated", "r1.pdf", {"skills": ["Python", "SQL"]})
        assert store.get_profile()["profile_json"]["skills"] == ["Python", "SQL"]

        # 3. Deactivate default workspace manually
        from sqlalchemy import text
        with store.engine.begin() as conn:
            conn.execute(text("UPDATE workspaces SET is_active = 0 WHERE workspace_id = 'ws_default_bob'"))

        # Verify _active_workspace_id returns None
        with store.engine.connect() as conn:
            assert store._active_workspace_id(conn) is None

        # 4. Save profile when default workspace exists but is_active=False:
        # Should reactivate default workspace without duplicate INSERT or IntegrityError
        store.save_profile("Resume 2", "r2.pdf", {"skills": ["Python", "FastAPI"]})

        ws_list_after = store.list_workspaces()
        assert len(ws_list_after) == 1
        assert ws_list_after[0]["workspace_id"] == "ws_default_bob"
        assert ws_list_after[0]["is_active"] is True
        assert store.get_profile()["profile_json"]["skills"] == ["Python", "FastAPI"]


def test_save_profile_preserves_active_custom_workspace(tmp_path: Path) -> None:
    """Verify that an existing active non-default workspace is preserved during save_profile."""
    db = tmp_path / "ws_custom_active.sqlite3"
    with JobStore(db, user_id="charlie") as store:
        # Create default workspace
        store.save_profile("Default Resume", "default.pdf", {"label": "default"})

        # Create and switch to a custom workspace
        custom_ws = store.create_workspace("Custom Active")
        store.switch_workspace(custom_ws["workspace_id"])

        # Save profile -> must save into custom workspace, NOT replace/reactivate default workspace
        store.save_profile("Custom Resume", "custom.pdf", {"label": "custom"})

        ws_list = store.list_workspaces()
        active_ws = next(w for w in ws_list if w["is_active"])
        assert active_ws["workspace_id"] == custom_ws["workspace_id"]
        assert store.get_profile()["profile_json"]["label"] == "custom"
