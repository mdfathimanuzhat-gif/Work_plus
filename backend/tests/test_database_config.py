from sqlalchemy.engine.url import make_url

from app.core.config import get_settings
from app.database.session import engine


def test_database_url_is_postgresql() -> None:
    url = make_url(get_settings().DATABASE_URL)
    assert url.get_backend_name() == "postgresql"
    assert engine.url.get_backend_name() == "postgresql"
