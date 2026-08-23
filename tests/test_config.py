from career_agent.config import normalize_database_url


def test_normalize_railway_postgres_url() -> None:
    url = "postgresql://user:password@postgres.railway.internal:5432/railway"
    expected = "postgresql+psycopg://user:password@postgres.railway.internal:5432/railway"
    assert normalize_database_url(url) == expected
