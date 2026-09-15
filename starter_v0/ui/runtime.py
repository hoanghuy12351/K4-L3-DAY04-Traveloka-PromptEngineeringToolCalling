from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from providers.base import ToolCall
from tools import TOOL_FUNCTIONS
from versioning import ArtifactVersion, artifact_version_dict


def now_iso() -> str:
    """Return a local ISO timestamp with enough precision for evidence."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def safe_slug(value: str) -> str:
    """Make a user-supplied label safe for a generated filename."""
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "session"


def trim_history(history: list[dict[str, str]], window: int) -> list[dict[str, str]]:
    """Keep complete user and assistant pairs from the recent conversation."""
    if window <= 0:
        return []
    return history[-window * 2:]


def json_text(value: Any, *, max_chars: int = 24000) -> str:
    """Serialize structured tool evidence without overflowing a model message."""
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if len(text) > max_chars:
        return text[:max_chars] + "\n...<truncated>"
    return text


def execute_tool_call(call: ToolCall) -> dict[str, Any]:
    """Execute an actual registered tool and retain any failure as evidence."""
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return {
            "tool": call.name,
            "args": call.args,
            "result": {
                "error": "unknown_tool",
                "message": f"No local implementation for {call.name}",
            },
        }
    try:
        result = func(**call.args)
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
    return {"tool": call.name, "args": call.args, "result": result}


def assistant_tool_message(response_text: str | None, calls: list[ToolCall]) -> dict[str, str]:
    """Preserve a real model tool-selection turn for the next model call."""
    call_summary = [{"name": call.name, "args": call.args} for call in calls]
    content = response_text or "I will call the selected travel tool(s)."
    return {
        "role": "assistant",
        "content": f"{content}\n\nTOOL_CALLS_JSON:\n{json_text(call_summary)}",
    }


def tool_results_message(events: list[dict[str, Any]]) -> dict[str, str]:
    """Return a UI-local, travel-specific transport message for real tool results."""
    return {
        "role": "user",
        "content": (
            "TOOL_RESULTS_JSON:\n"
            f"{json_text(events)}\n\n"
            "Use only these tool results as factual travel evidence. Do not invent prices, "
            "availability, IDs, or booking status. If required travel information is still "
            "missing, ask the user. Otherwise answer the user's latest request directly. "
            "Remember that the travel catalog is fictional/static classroom data, not live "
            "market availability."
        ),
    }


def structured_response(text: str) -> dict[str, Any] | None:
    """Expose a JSON reply for friendly rendering without changing stored text."""
    candidate = text.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3:
            candidate = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(candidate)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or not isinstance(value.get("reply"), str):
        return None
    return value


class TravelUISession:
    """Maintain one isolated browser conversation and its evidence transcript."""

    def __init__(
        self,
        *,
        provider: Any,
        provider_name: str,
        model: str | None,
        version: str,
        artifact_version: ArtifactVersion,
        system_prompt: str,
        system_prompt_path: Path,
        tools_path: Path,
        tools: list[dict[str, Any]],
        transcripts_dir: Path,
        history_window: int,
        max_tool_rounds: int,
    ) -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.model = model
        self.version = version
        self.artifact_version = artifact_version
        self.system_prompt = system_prompt
        self.system_prompt_path = system_prompt_path
        self.tools_path = tools_path
        self.tools = tools
        self.transcripts_dir = transcripts_dir
        self.history_window = history_window
        self.max_tool_rounds = max_tool_rounds
        self.session_id = uuid.uuid4().hex
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        self.transcript_id = "_".join(
            ["ui", safe_slug(version), safe_slug(provider_name), timestamp, self.session_id[:8]]
        )
        self.transcript_path = transcripts_dir / f"{self.transcript_id}.transcript.json"
        self.history: list[dict[str, str]] = []
        self.turn_index = 0
        self.lock = threading.RLock()
        self.last_save_error: str | None = None
        self.transcript: dict[str, Any] = {
            "transcript_id": self.transcript_id,
            "source": "web_ui",
            **artifact_version_dict(artifact_version),
            "provider": provider_name,
            "model": model,
            "system_prompt": str(system_prompt_path),
            "tools": str(tools_path),
            "history_window": history_window,
            "max_tool_rounds": max_tool_rounds,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "turns": [],
        }
        self._write_transcript()

    def _write_transcript(self) -> bool:
        """Write the active transcript, retaining a non-secret error if it fails."""
        self.transcript["updated_at"] = now_iso()
        try:
            self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
            self.transcript_path.write_text(
                json.dumps(self.transcript, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            self.last_save_error = f"{type(exc).__name__}: {exc}"
            return False
        self.last_save_error = None
        return True

    def info(self) -> dict[str, Any]:
        """Return safe session and transcript status for the browser."""
        return {
            "session_id": self.session_id,
            "transcript_id": self.transcript_id,
            "transcript_path": str(self.transcript_path),
            "saved": self.last_save_error is None and self.transcript_path.exists(),
            "last_saved_at": self.transcript.get("updated_at"),
            "transcript_error": self.last_save_error,
        }

    def _run_tool_loop(self, user_text: str) -> dict[str, Any]:
        """Call the provider and registered tools until a final answer or pause state."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            *trim_history(self.history, self.history_window),
            {"role": "user", "content": user_text},
        ]
        working_messages = list(messages)
        rounds: list[dict[str, Any]] = []
        all_tool_events: list[dict[str, Any]] = []

        for round_index in range(1, self.max_tool_rounds + 1):
            response = self.provider.complete(
                working_messages,
                self.tools,
                model=self.model,
                temperature=0.0,
            )
            calls = response.tool_calls
            round_record: dict[str, Any] = {
                "round": round_index,
                "assistant_text": response.text,
                "tool_calls": [{"name": call.name, "args": call.args} for call in calls],
                "tool_results": [],
            }

            if not calls:
                rounds.append(round_record)
                final_text = response.text or ""
                return {
                    "status": "answered",
                    "assistant_text": final_text,
                    "structured_assistant": structured_response(final_text),
                    "rounds": rounds,
                    "tool_events": all_tool_events,
                }

            working_messages.append(assistant_tool_message(response.text, calls))
            non_clarification_events: list[dict[str, Any]] = []
            for call in calls:
                event = execute_tool_call(call)
                round_record["tool_results"].append(event)
                all_tool_events.append(event)
                result = event.get("result", {})
                if isinstance(result, dict) and result.get("awaiting_user"):
                    question = result.get("question") or call.args.get("question") or "Please provide more details."
                    rounds.append(round_record)
                    return {
                        "status": "waiting_for_user",
                        "assistant_text": question,
                        "structured_assistant": None,
                        "rounds": rounds,
                        "tool_events": all_tool_events,
                    }
                non_clarification_events.append(event)

            rounds.append(round_record)
            working_messages.append(tool_results_message(non_clarification_events))

        message = f"Stopped after {self.max_tool_rounds} tool rounds. Inspect the transcript for details."
        return {
            "status": "max_tool_rounds",
            "assistant_text": message,
            "structured_assistant": None,
            "rounds": rounds,
            "tool_events": all_tool_events,
        }

    def send(self, user_text: str) -> dict[str, Any]:
        """Run one user turn, save its exact evidence, and return browser-ready data."""
        cleaned_text = user_text.strip()
        if not cleaned_text:
            raise ValueError("Message must not be empty.")

        with self.lock:
            self.turn_index += 1
            turn_record: dict[str, Any] = {
                "turn_index": self.turn_index,
                "started_at": now_iso(),
                "user": cleaned_text,
                "status": "started",
                "assistant_text": None,
                "rounds": [],
                "tool_events": [],
            }
            try:
                result = self._run_tool_loop(cleaned_text)
                turn_record.update(result)
                self.history.append({"role": "user", "content": cleaned_text})
                self.history.append({"role": "assistant", "content": result["assistant_text"]})
            except Exception as exc:
                result = {
                    "status": "provider_error",
                    "assistant_text": "",
                    "structured_assistant": None,
                    "rounds": [],
                    "tool_events": [],
                    "error": f"{type(exc).__name__}: {exc}",
                }
                turn_record.update(result)

            turn_record["ended_at"] = now_iso()
            self.transcript["turns"].append(turn_record)
            saved = self._write_transcript()
            return {
                "session_id": self.session_id,
                "turn_index": self.turn_index,
                **result,
                "transcript": {**self.info(), "saved": saved},
            }

    def transcript_data(self) -> dict[str, Any]:
        """Return a detached JSON-safe copy of the active transcript."""
        with self.lock:
            return json.loads(json.dumps(self.transcript, ensure_ascii=False, default=str))
