# Qobuz no longer accepts email/password on user/login. Like the web
# player, we send the user to the Qobuz sign-in page, which redirects
# back with an authorization code that is exchanged for a token.

import logging
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from qobuz_dl.color import YELLOW
from qobuz_dl.exceptions import AuthenticationError

SIGNIN_URL = "https://www.qobuz.com/signin/oauth"
CALLBACK_URL = "https://www.qobuz.com/api.json/0.2/oauth/callback"

logger = logging.getLogger(__name__)


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        self.server.code = query.get("code_autorisation", [None])[0]
        message = (
            "Logged in to Qobuz, you can close this tab."
            if self.server.code
            else "No authorization code received."
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def log_message(self, format, *args):
        pass


def get_auth_code(app_id):
    server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
    server.code = None
    redirect_url = f"http://127.0.0.1:{server.server_port}/"
    url = f"{SIGNIN_URL}?" + urlencode(
        {"ext_app_id": app_id, "redirect_url": redirect_url}
    )
    logger.info(f"{YELLOW}Log in to Qobuz in your browser:\n{url}")
    webbrowser.open(url)
    try:
        while server.code is None:
            server.handle_request()
    finally:
        server.server_close()
    return server.code


def get_user_auth_token(app_id, private_key):
    code = get_auth_code(app_id)
    r = requests.get(
        CALLBACK_URL,
        params={"code": code, "private_key": private_key},
        headers={"X-App-Id": str(app_id)},
    )
    if not r.ok:
        raise AuthenticationError(f"Qobuz rejected the login: {r.text}")
    return r.json()["token"]
