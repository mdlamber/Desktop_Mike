from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]
TOKEN_URI = 'https://oauth2.googleapis.com/token'


def get_id_token(config: dict) -> str:
    creds = Credentials(
        token=None,
        refresh_token=config['refresh_token'],
        token_uri=TOKEN_URI,
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    if not creds.id_token:
        raise ValueError(
            "Token refresh succeeded but no id_token was returned. "
            "Ensure the 'openid' scope is requested."
        )
    return creds.id_token


def run_oauth_flow(config: dict) -> dict:
    client_config = {
        'installed': {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': TOKEN_URI,
            'redirect_uris': ['http://localhost'],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=8085, open_browser=True)
    if not creds.refresh_token:
        raise RuntimeError(
            "OAuth flow completed but no refresh_token was issued. "
            "Ensure 'offline' access is enabled for this OAuth client."
        )
    config['refresh_token'] = creds.refresh_token
    return config


def ensure_authenticated(config: dict) -> dict:
    if not config.get('refresh_token'):
        config = run_oauth_flow(config)
    return config
