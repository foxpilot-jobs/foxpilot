"""Tests for server-side pagination, filtering, and sorting."""

from pathlib import Path

from fastapi.testclient import TestClient

from career_agent.config import AppConfig
from career_agent.storage import JobStore
from career_agent.storage.database import decode_cursor, encode_cursor
from services.api.app import create_app

# -- Cursor encoding/decoding --


def test_cursor_round_trip() -> None:
    cursor = encode_cursor("2025-01-01 12:00:00", "job-123")
    parts = decode_cursor(cursor)
    assert parts is not None
    assert parts[0] == "2025-01-01 12:00:00"
    assert parts[1] == "job-123"


def test_decode_cursor_returns_none_for_invalid() -> None:
    assert decode_cursor("not-valid-base64!!!") is None
    assert decode_cursor("") is None


# -- Jobs pagination --


def test_list_jobs_returns_paginated_envelope(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        for i in range(5):
            store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )

    with JobStore(config.database_path) as store:
        result = store.list_jobs(limit=3)
        assert "items" in result
        assert "next_cursor" in result
        assert "total" in result
        assert result["total"] == 5
        assert len(result["items"]) == 3
        assert result["next_cursor"] is not None


def test_list_jobs_cursor_paginates(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        for i in range(5):
            store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )

    with JobStore(config.database_path) as store:
        page1 = store.list_jobs(limit=3)
        assert len(page1["items"]) == 3
        page2 = store.list_jobs(limit=3, cursor=page1["next_cursor"])
        assert len(page2["items"]) == 2
        assert page2["next_cursor"] is None
        # No overlap
        ids1 = {j["job_id"] for j in page1["items"]}
        ids2 = {j["job_id"] for j in page2["items"]}
        assert ids1.isdisjoint(ids2)


def test_list_jobs_query_filter(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        store.upsert_job(
            {"source": "test", "source_job_id": "1", "title": "Frontend Engineer"}
        )
        store.upsert_job(
            {"source": "test", "source_job_id": "2", "title": "Data Engineer"}
        )
        store.upsert_job(
            {
                "source": "test",
                "source_job_id": "3",
                "title": "Product Manager",
                "company": "DataCorp",
            }
        )

    with JobStore(config.database_path) as store:
        result = store.list_jobs(query_text="Data")
        assert result["total"] == 2  # "Data Engineer" + "DataCorp"
        titles = {j["title"] for j in result["items"]}
        assert "Data Engineer" in titles


def test_list_jobs_sort_by_title(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        store.upsert_job(
            {"source": "test", "source_job_id": "1", "title": "Zebra Tamer"}
        )
        store.upsert_job(
            {"source": "test", "source_job_id": "2", "title": "Apple Farmer"}
        )

    with JobStore(config.database_path) as store:
        result = store.list_jobs(sort="title")
        assert result["items"][0]["title"] == "Apple Farmer"
        assert result["items"][1]["title"] == "Zebra Tamer"


def test_list_jobs_source_filter(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        store.upsert_job({"source": "lever", "source_job_id": "1", "title": "A"})
        store.upsert_job({"source": "greenhouse", "source_job_id": "2", "title": "B"})

    with JobStore(config.database_path) as store:
        result = store.list_jobs(source="lever")
        assert result["total"] == 1
        assert result["items"][0]["source"] == "lever"


# -- Matches pagination --


def test_list_matches_returns_paginated_envelope(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        for i in range(5):
            job_id = store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )
            store.save_match(
                job_id,
                f"hash-{i}",
                "ollama",
                "model",
                {
                    "match_score": 80 + i,
                    "recommendation": "APPLY" if i < 3 else "CONSIDER",
                },
            )

    with JobStore(config.database_path, user_id="user-a") as store:
        result = store.list_matches(limit=3)
        assert "items" in result
        assert "next_cursor" in result
        assert "total" in result
        assert result["total"] == 5
        assert len(result["items"]) == 3


def test_list_matches_recommendation_filter(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        for i, rec in enumerate(["APPLY", "CONSIDER", "SKIP", "APPLY"]):
            job_id = store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )
            store.save_match(
                job_id,
                f"hash-{i}",
                "ollama",
                "model",
                {"match_score": 80, "recommendation": rec},
            )

    with JobStore(config.database_path, user_id="user-a") as store:
        result = store.list_matches(recommendation="APPLY")
        assert result["total"] == 2
        for item in result["items"]:
            assert item["match"]["recommendation"] == "APPLY"


def test_list_matches_sort_by_score(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        for i, score in enumerate([60, 90, 75]):
            job_id = store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )
            store.save_match(
                job_id,
                f"hash-{i}",
                "ollama",
                "model",
                {"match_score": score, "recommendation": "APPLY"},
            )

    with JobStore(config.database_path, user_id="user-a") as store:
        result = store.list_matches(sort="score")
        scores = [item["match"]["match_score"] for item in result["items"]]
        assert scores == [90, 75, 60]


# -- Applications pagination --


def test_list_applications_returns_paginated_envelope(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        for i in range(5):
            job_id = store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )
            store.save_application(job_id, status="saved")

    with JobStore(config.database_path, user_id="user-a") as store:
        result = store.list_applications(limit=3)
        assert "items" in result
        assert "next_cursor" in result
        assert "total" in result
        assert result["total"] == 5
        assert len(result["items"]) == 3


def test_list_applications_status_filter(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        for i, status in enumerate(
            ["saved", "applied", "interviewing", "applied", "offered"]
        ):
            job_id = store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )
            store.save_application(job_id, status=status)

    with JobStore(config.database_path, user_id="user-a") as store:
        result = store.list_applications(status_filter="applied")
        assert result["total"] == 2
        for item in result["items"]:
            assert item["status"] == "applied"


# -- API endpoint tests --


def test_api_jobs_pagination(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        for i in range(5):
            store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )

    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    response = client.get("/api/v1/jobs?limit=3")
    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 3
    assert body["total"] == 5
    assert body["next_cursor"] is not None

    # Second page
    response2 = client.get(f"/api/v1/jobs?limit=3&cursor={body['next_cursor']}")
    body2 = response2.json()
    assert len(body2["items"]) == 2


def test_api_jobs_query_filter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        store.upsert_job(
            {"source": "test", "source_job_id": "1", "title": "Python Developer"}
        )
        store.upsert_job(
            {"source": "test", "source_job_id": "2", "title": "Go Developer"}
        )

    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    response = client.get("/api/v1/jobs?query=Python")
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Python Developer"


def test_api_matches_pagination_and_filter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        for i, rec in enumerate(["APPLY", "CONSIDER", "APPLY"]):
            job_id = store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )
            store.save_match(
                job_id,
                f"hash-{i}",
                "test",
                "model",
                {"match_score": 80 + i, "recommendation": rec},
            )

    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    response = client.get("/api/v1/matches?recommendation=APPLY")
    body = response.json()
    assert body["total"] == 2
    for item in body["items"]:
        assert item["match"]["recommendation"] == "APPLY"


def test_api_applications_pagination(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        for i in range(5):
            job_id = store.upsert_job(
                {"source": "test", "source_job_id": str(i), "title": f"Role {i}"}
            )
            store.save_application(job_id, status="saved")

    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    response = client.get("/api/v1/applications?limit=3")
    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 3
    assert body["total"] == 5
