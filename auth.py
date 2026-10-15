import base64
import hashlib
import http.server
import json
import platform
import threading
import time
import urllib.parse
import uuid
import webbrowser

from curl_cffi import requests

from config import CLIENT_ID, OAUTH_URL, PROTOCOL_VERSION, SESSION_FILE

USER_AGENT = f"NexusApiClient/{PROTOCOL_VERSION} ({platform.system()} {platform.release()}; x64) Python"

token_lock = threading.Lock()
_local = threading.local()


def http_client():
    if not hasattr(_local, "session"):
        _local.session = requests.Session(impersonate="chrome", timeout=30)
    return _local.session


def jwt_payload(token):
    try:
        part = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    except (IndexError, ValueError):
        return {}


def post_token(data):
    resp = http_client().post(f"{OAUTH_URL}/token", data=data, headers={"User-Agent": USER_AGENT})
    if not resp.ok:
        raise RuntimeError(f"token endpoint {resp.status_code}: {resp.text}")
    return resp.json()


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    result = {}

    def do_GET(self):
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        if "code" in query or "error" in query:
            CallbackHandler.result = query
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h1>Login complete, you can close this window.</h1>")

    def log_message(self, *args):
        pass


def browser_login():
    server = http.server.HTTPServer(("127.0.0.1", 0), CallbackHandler)
    redirect_uri = f"http://127.0.0.1:{server.server_address[1]}"
    verifier = base64.b64encode(uuid.uuid1().hex.encode()).decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = str(uuid.uuid1())
    params = {
        "response_type": "code",
        "scope": "openid profile email",
        "code_challenge_method": "S256",
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
    }
    print("Opening browser for Nexus Mods login...")
    webbrowser.open(f"{OAUTH_URL}/authorize?{urllib.parse.urlencode(params)}")

    CallbackHandler.result = {}
    deadline = time.time() + 300
    server.timeout = 1
    while not CallbackHandler.result and time.time() < deadline:
        server.handle_request()
    server.server_close()

    result = CallbackHandler.result
    if result.get("state") != state or "code" not in result:
        raise RuntimeError(f"login failed: {result or 'timed out'}")
    return post_token({
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "code": result["code"],
        "code_verifier": verifier,
    })


def save_session(reply):
    session = {"token": reply["access_token"], "refreshToken": reply["refresh_token"]}
    SESSION_FILE.write_text(json.dumps(session, indent=2))
    return session


def get_token():
    with token_lock:
        if SESSION_FILE.exists():
            session = json.loads(SESSION_FILE.read_text())
            if jwt_payload(session["token"]).get("exp", 0) - time.time() > 60:
                return session["token"]
            try:
                return save_session(post_token({
                    "grant_type": "refresh_token",
                    "client_id": CLIENT_ID,
                    "refresh_token": session["refreshToken"],
                }))["token"]
            except RuntimeError as e:
                if "invalid_grant" not in str(e):
                    raise
        return save_session(browser_login())["token"]
