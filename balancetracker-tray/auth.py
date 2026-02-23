from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['openid', 'email', 'profile']
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
    creds = flow.run_local_server(port=0, open_browser=True)
    config['refresh_token'] = creds.refresh_token
    return config


def ensure_authenticated(config: dict) -> dict:
    if not config.get('refresh_token'):
        config = run_oauth_flow(config)
    return config
