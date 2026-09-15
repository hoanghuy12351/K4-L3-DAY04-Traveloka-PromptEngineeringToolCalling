from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


UI_DIR = Path(__file__).resolve().parent
STARTER_DIR = UI_DIR.parent
if str(STARTER_DIR) not in sys.path:
    sys.path.insert(0, str(STARTER_DIR))

from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import build_artifact_version, short_hash
from runtime import TravelUISession


ARTIFACTS_DIR = STARTER_DIR / "artifacts"
STATIC_DIR = UI_DIR / "static"
DEMO_SCENARIOS_PATH = UI_DIR / "demo_scenarios.json"
TRANSCRIPTS_DIR = STARTER_DIR / "transcripts"
SESSION_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


class UIState:
    """Hold shared immutable runtime configuration and isolated active sessions."""

    def __init__(self, args: argparse.Namespace) -> None:
        load_lab_env(STARTER_DIR)
        self.provider_name = args.provider
        self.provider = make_provider(args.provider)
        self.model = args.model or getattr(self.provider, "default_model", None)
        self.version = args.version
        self.system_prompt_path = args.system_prompt.resolve()
        self.tools_path = args.tools.resolve()
        self.system_prompt = self.system_prompt_path.read_text(encoding="utf-8")
        self.tool_declarations = load_tool_declarations(self.tools_path)
        self.openai_tools = to_openai_tools(self.tool_declarations)
        self.artifact_version = build_artifact_version(args.version, self.system_prompt_path, self.tools_path)
        self.history_window = args.history_window
        self.max_tool_rounds = args.max_tool_rounds
        self.transcripts_dir = args.transcripts_dir.resolve()
        self.demo_scenarios = json.loads(DEMO_SCENARIOS_PATH.read_text(encoding="utf-8"))
        self.sessions: dict[str, TravelUISession] = {}
        self.lock = threading.RLock()

    def meta(self) -> dict[str, Any]:
        """Return metadata that can safely be sent to a local browser."""
        return {
            "provider": self.provider_name,
            "model": self.model,
            "version": self.version,
            "artifact_version": self.artifact_version.artifact_version,
            "prompt_hash": self.artifact_version.prompt_hash,
            "tools_hash": self.artifact_version.tools_hash,
            "prompt_hash_short": short_hash(self.artifact_version.prompt_hash),
            "tools_hash_short": short_hash(self.artifact_version.tools_hash),
            "tool_count": len(self.tool_declarations),
            "tool_names": [item["name"] for item in self.tool_declarations],
            "tool_declarations": self.tool_declarations,
            "system_prompt_path": str(self.system_prompt_path),
            "tools_path": str(self.tools_path),
            "history_window": self.history_window,
            "max_tool_rounds": self.max_tool_rounds,
            "fictional_data": True,
        }

    def create_session(self) -> TravelUISession:
        """Create a new independent conversation with a separate transcript."""
        session = TravelUISession(
            provider=self.provider,
            provider_name=self.provider_name,
            model=self.model,
            version=self.version,
            artifact_version=self.artifact_version,
            system_prompt=self.system_prompt,
            system_prompt_path=self.system_prompt_path,
            tools_path=self.tools_path,
            tools=self.openai_tools,
            transcripts_dir=self.transcripts_dir,
            history_window=self.history_window,
            max_tool_rounds=self.max_tool_rounds,
        )
        with self.lock:
            self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> TravelUISession | None:
        """Resolve only an active server-owned session identifier."""
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            return None
        with self.lock:
            return self.sessions.get(session_id)

    def reset_session(self, session_id: str) -> TravelUISession | None:
        """Preserve the old transcript and replace the current conversation."""
        with self.lock:
            if session_id not in self.sessions:
                return None
            self.sessions.pop(session_id)
        return self.create_session()


class TravelUIHandler(BaseHTTPRequestHandler):
    """Serve static assets and a narrow JSON API for the local UI."""

    server_version = "TravelPlannerUI/1.0"

    @property
    def state(self) -> UIState:
        return self.server.ui_state  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        """Keep server output concise without logging request bodies."""
        sys.stderr.write("[ui] " + (format % args) + "\n")

    def _send_json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"error": message})

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_error_json(HTTPStatus.NOT_FOUND, "Not found.")
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix in {".html", ".js", ".css"}:
            content_type += "; charset=utf-8"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any] | None:
        length_text = self.headers.get("Content-Length", "0")
        try:
            length = int(length_text)
        except ValueError:
            self._send_error_json(HTTPStatus.BAD_REQUEST, "Invalid Content-Length.")
            return None
        if length <= 0 or length > 100_000:
            self._send_error_json(HTTPStatus.BAD_REQUEST, "Request body must be between 1 and 100000 bytes.")
            return None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_error_json(HTTPStatus.BAD_REQUEST, "Request body must be valid UTF-8 JSON.")
            return None
        if not isinstance(payload, dict):
            self._send_error_json(HTTPStatus.BAD_REQUEST, "Request JSON must be an object.")
            return None
        return payload

    def _discard_optional_body(self) -> bool:
        """Consume optional JSON sent to endpoints that do not need a payload."""
        length_text = self.headers.get("Content-Length", "0")
        try:
            length = int(length_text)
        except ValueError:
            self._send_error_json(HTTPStatus.BAD_REQUEST, "Invalid Content-Length.")
            return False
        if length < 0 or length > 100_000:
            self._send_error_json(HTTPStatus.BAD_REQUEST, "Request body is too large.")
            return False
        if length:
            self.rfile.read(length)
        return True

    def _session_from_path(self, path: str, suffix: str = "") -> TravelUISession | None:
        prefix = "/api/session/"
        if not path.startswith(prefix) or (suffix and not path.endswith(suffix)):
            return None
        session_id = path[len(prefix):]
        if suffix:
            session_id = session_id[: -len(suffix)]
        return self.state.get_session(session_id)

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/":
            self._send_file(STATIC_DIR / "index.html")
            return
        if path in {"/app.js", "/styles.css"}:
            self._send_file(STATIC_DIR / path.lstrip("/"))
            return
        if path == "/api/meta":
            self._send_json(HTTPStatus.OK, self.state.meta())
            return
        if path == "/api/demo-scenarios":
            self._send_json(HTTPStatus.OK, self.state.demo_scenarios)
            return
        if path.startswith("/api/session/") and path.endswith("/transcript/download"):
            session = self._session_from_path(path, "/transcript/download")
            if not session:
                self._send_error_json(HTTPStatus.NOT_FOUND, "Unknown session.")
                return
            body = json.dumps(session.transcript_data(), ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{session.transcript_id}.json"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith("/api/session/") and path.endswith("/transcript"):
            session = self._session_from_path(path, "/transcript")
            if not session:
                self._send_error_json(HTTPStatus.NOT_FOUND, "Unknown session.")
                return
            self._send_json(HTTPStatus.OK, session.transcript_data())
            return
        self._send_error_json(HTTPStatus.NOT_FOUND, "Not found.")

    def do_POST(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/api/session":
            if not self._discard_optional_body():
                return
            session = self.state.create_session()
            self._send_json(HTTPStatus.CREATED, {"session": session.info(), "meta": self.state.meta()})
            return
        if path.startswith("/api/session/") and path.endswith("/chat"):
            session = self._session_from_path(path, "/chat")
            if not session:
                self._send_error_json(HTTPStatus.NOT_FOUND, "Unknown session.")
                return
            payload = self._read_json_body()
            if payload is None:
                return
            message = payload.get("message")
            if not isinstance(message, str):
                self._send_error_json(HTTPStatus.BAD_REQUEST, "message must be a string.")
                return
            if len(message) > 50_000:
                self._send_error_json(HTTPStatus.BAD_REQUEST, "message is too long.")
                return
            try:
                self._send_json(HTTPStatus.OK, session.send(message))
            except ValueError as exc:
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if path.startswith("/api/session/") and path.endswith("/reset"):
            if not self._discard_optional_body():
                return
            session_id = path[len("/api/session/"):-len("/reset")]
            session = self.state.reset_session(session_id)
            if not session:
                self._send_error_json(HTTPStatus.NOT_FOUND, "Unknown session.")
                return
            self._send_json(HTTPStatus.OK, {"session": session.info(), "meta": self.state.meta()})
            return
        self._send_error_json(HTTPStatus.NOT_FOUND, "Not found.")


def parse_args() -> argparse.Namespace:
    """Parse the standalone UI's intentionally small local-server interface."""
    parser = argparse.ArgumentParser(description="Run the local AI Travel Planner web UI.")
    parser.add_argument("--provider", choices=["openai", "openrouter", "anthropic", "gemini"], required=True)
    parser.add_argument("--version", required=True, help="Artifact version label, for example v3.")
    parser.add_argument("--model", default=None, help="Override the provider's default model.")
    parser.add_argument("--host", default="127.0.0.1", help="Local bind host. Default is 127.0.0.1.")
    parser.add_argument("--port", type=int, default=7860, help="Local server port.")
    parser.add_argument("--history-window", type=int, default=5, help="Recent user/assistant pairs retained per session.")
    parser.add_argument("--max-tool-rounds", type=int, default=4, help="Maximum real model/tool rounds per chat turn.")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=TRANSCRIPTS_DIR)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535.")
    if args.history_window < 0:
        parser.error("--history-window must be zero or greater.")
    if args.max_tool_rounds < 1:
        parser.error("--max-tool-rounds must be at least 1.")
    return args


def main() -> None:
    """Start the local threaded HTTP server without exposing provider credentials."""
    args = parse_args()
    state = UIState(args)
    server = ThreadingHTTPServer((args.host, args.port), TravelUIHandler)
    server.ui_state = state  # type: ignore[attr-defined]
    print(f"AI Travel Planner UI running at http://{args.host}:{args.port}")
    print(f"Provider={state.provider_name} Model={state.model} Artifact={state.artifact_version.artifact_version}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping UI server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
