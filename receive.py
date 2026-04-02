import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

import requests
import websocket
from dotenv import load_dotenv
from loguru import logger

from util import getConfig

ATTACHMENT_NOTICE = "You received a file: attachment.txt"
PING_INTERVAL_SECONDS = 30
PING_TIMEOUT_SECONDS = 10
RECONNECT_DELAY_SECONDS = 5
LOG_LEVEL_ENV = "LOG_LEVEL"
WEBSOCKET_TRACE_ENV = "NTFY_WS_TRACE"
RECEIVE_STATE_FILENAME = "receive_state.json"

_ENV_PATH = Path(__file__).resolve().parent / ".env"
_STATE_PATH = Path(__file__).resolve().parent / RECEIVE_STATE_FILENAME
load_dotenv(dotenv_path=_ENV_PATH)


def _configure_logging() -> None:
    log_path = Path(__file__).resolve().parent / "receive.log"
    logger.remove()
    log_level = os.getenv(LOG_LEVEL_ENV, "INFO")
    logger.add(
        str(log_path),
        rotation="100 KB",
        retention=5,
        enqueue=False,
        level=log_level,
    )
    logger.add(sys.stdout, level=log_level)


def _load_lineate():
    convert_links_dir = getConfig()["convertLinksDir"]
    if convert_links_dir not in sys.path:
        sys.path.insert(0, convert_links_dir)
    import lineate

    return lineate


def _ensure_clipboard_ready() -> None:
    if not os.getenv("DISPLAY"):
        raise RuntimeError("DISPLAY is not set; X11 clipboard is unavailable.")
    if shutil.which("xclip") is None:
        raise RuntimeError("xclip not found on PATH.")


def _copy_to_clipboard(text: str) -> None:
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=text.encode("utf-8"),
        check=True,
        close_fds=True,
    )


def _fetch_attachment_text(attachment_id: str) -> str:
    attachment_url = f"https://ntfy.sh/file/{attachment_id}.txt"
    response = requests.get(attachment_url, timeout=15)
    response.raise_for_status()
    return response.text


def _load_receive_state(state_path: Path = _STATE_PATH) -> dict[str, str]:
    if not state_path.exists():
        return {}

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception(f"Failed to load receive state from {state_path}.")
        return {}

    if not isinstance(state, dict):
        logger.warning(f"Ignoring malformed receive state in {state_path}.")
        return {}

    return {
        topic: message_id
        for topic, message_id in state.items()
        if isinstance(topic, str) and isinstance(message_id, str) and message_id
    }


def _load_last_processed_message_id(
    topic: str, state_path: Path = _STATE_PATH
) -> str | None:
    return _load_receive_state(state_path).get(topic)


def _store_last_processed_message_id(
    topic: str, message_id: str, state_path: Path = _STATE_PATH
) -> None:
    state = _load_receive_state(state_path)
    state[topic] = message_id
    state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")


def _build_ws_url(topic: str, last_processed_message_id: str | None) -> str:
    ws_url = f"wss://ntfy.sh/{topic}/ws"
    if not last_processed_message_id:
        return ws_url
    return f"{ws_url}?{urlencode({'since': last_processed_message_id})}"


def resolve_message_text(
    data: dict, fetch_attachment_text: Callable[[str], str]
) -> str | None:
    message_text = data.get("message")
    if not message_text:
        return None

    if message_text != ATTACHMENT_NOTICE:
        return message_text

    attachment_id = data.get("id")
    if not attachment_id:
        raise ValueError("Attachment message missing id.")

    return fetch_attachment_text(attachment_id)


def _handle_message(data: dict, topic: str) -> None:
    message_text = resolve_message_text(data, _fetch_attachment_text)
    if message_text is None:
        return

    logger.info(f"Received message ({len(message_text)} chars).")
    _copy_to_clipboard(message_text)
    lineate = _load_lineate()
    lineate.main(
        message_text,
        openInBrowser=True,
        forceConvertAllUrls=False,
        forceNoConvert=True,
    )

    message_id = data.get("id")
    if isinstance(message_id, str) and message_id:
        _store_last_processed_message_id(topic, message_id)


def _on_message(ws, message: str, topic: str) -> None:
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        logger.exception("Received invalid JSON payload.")
        ws.close(status=1003, reason="invalid json")
        return

    try:
        _handle_message(data, topic)
    except Exception:
        logger.exception("Failed while handling message payload.")
        ws.close(status=1011, reason="handler error")


def _on_error(_ws, error) -> None:
    logger.error(f"WebSocket error: {error}")


def _on_close(_ws, close_status_code, close_msg) -> None:
    logger.warning(f"WebSocket closed ({close_status_code}): {close_msg}")


def _on_open(_ws) -> None:
    logger.info("WebSocket connection opened.")


def _connect_loop(topic: str) -> None:
    ws = None
    while True:
        last_processed_message_id = _load_last_processed_message_id(topic)
        ws_url = _build_ws_url(topic, last_processed_message_id)
        if last_processed_message_id:
            logger.info(f"Resuming from ntfy message {last_processed_message_id}.")
        logger.info(f"Connecting to {ws_url}")
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=lambda current_ws, message: _on_message(
                current_ws, message, topic
            ),
            on_error=_on_error,
            on_close=_on_close,
            on_open=_on_open,
        )
        ws.run_forever(
            ping_interval=PING_INTERVAL_SECONDS,
            ping_timeout=PING_TIMEOUT_SECONDS,
        )
        logger.warning(
            f"WebSocket disconnected; reconnecting in {RECONNECT_DELAY_SECONDS}s."
        )
        time.sleep(RECONNECT_DELAY_SECONDS)


def lfg() -> None:
    _configure_logging()
    try:
        _ensure_clipboard_ready()
    except RuntimeError as error:
        logger.error(str(error))
        sys.exit(1)

    topic = os.getenv("NTFY_RECEIVE_TOPIC")
    if not topic:
        logger.error(
            "NTFY_RECEIVE_TOPIC not found. Set it in .env or the environment."
        )
        sys.exit(1)

    websocket.enableTrace(os.getenv(WEBSOCKET_TRACE_ENV, "").lower() in {"1", "true"})

    try:
        _connect_loop(topic)
    except KeyboardInterrupt:
        logger.info("Shutdown requested; exiting.")


if __name__ == "__main__":
    lfg()
