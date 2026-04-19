import pytest
from unittest.mock import patch

from app.broker.kiwoom_auth import get_token, clear_token_cache, KiwoomToken
from app.core.config import Settings


@pytest.fixture(autouse=True)
def reset_token_cache():
    clear_token_cache()
    yield
    clear_token_cache()


@pytest.fixture
def paper_settings():
    return Settings(
        TRADING_MODE="paper",
        KIWOOM_MOCK_APP_KEY="test_app_key",
        KIWOOM_MOCK_APP_SECRET="test_app_secret",
        KIWOOM_MOCK_API_BASE_URL="https://mockapi.kiwoom.com",
        KIWOOM_TOKEN_PATH="/oauth2/tokenP",
    )


@pytest.mark.vcr
async def test_get_token_returns_bearer_token(paper_settings):
    with patch("app.broker.kiwoom_auth.settings", paper_settings):
        token = await get_token()

    assert isinstance(token, KiwoomToken)
    assert token.access_token == "test_bearer_token_abc123xyz"
    assert token.token_type == "Bearer"
    assert token.expires_at > 0


@pytest.mark.vcr
async def test_get_token_caches_result(paper_settings):
    with patch("app.broker.kiwoom_auth.settings", paper_settings):
        token1 = await get_token()
        token2 = await get_token()

    # second call must reuse the cached token without a second HTTP request
    assert token1 is token2


@pytest.mark.vcr
async def test_get_token_uses_mock_credentials_in_paper_mode(paper_settings):
    with patch("app.broker.kiwoom_auth.settings", paper_settings):
        token = await get_token()

    # cassette only contains mock credentials — token issued means correct creds were sent
    assert token.access_token == "test_bearer_token_abc123xyz"
