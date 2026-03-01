import argparse
import os
import subprocess
import sys
from pathlib import Path

import pyperclip
import requests
from dotenv import load_dotenv
from loguru import logger

from util import getConfig

load_dotenv()

_logger_configured = False
MAX_NON_FILE_MESSAGE_BYTES = 3500
SEND_RAW_WORKFLOW = "send_ntfy_raw"
SEND_CONVERT_WORKFLOW = "send_ntfy_convert"
SEND_URL_QUEUE_NAME = "clipboard_send_urls"


def _configure_logging():
    global _logger_configured
    if _logger_configured:
        return
    logger.remove()
    logger.add("send.log", rotation="30 KB", retention=5, enqueue=False)
    logger.add(sys.stdout, level="INFO")
    _logger_configured = True


def get_selected_text():
    try:
        selected_text = subprocess.check_output(
            ["xclip", "-o", "-selection", "primary"],
            stderr=subprocess.STDOUT,
            text=True,
        )
        return selected_text
    except subprocess.CalledProcessError:
        return None


def _is_urls_and_whitespace_only(text, urls):
    remaining_text = text
    for url in urls:
        if not url:
            continue
        if "://" not in url:
            if url.startswith("/"):
                remaining_text = remaining_text.replace(f"file://{url}", "")
            else:
                resolved_path = str(Path(url).expanduser().resolve())
                remaining_text = remaining_text.replace(f"file://{resolved_path}", "")
        remaining_text = remaining_text.replace(url, "")
    return remaining_text.strip() == ""


def _load_lineate():
    convert_links_dir = getConfig()["convertLinksDir"]
    if convert_links_dir not in sys.path:
        sys.path.insert(0, convert_links_dir)
    import lineate

    return lineate


def _show_desktop_error(message: str) -> None:
    try:
        subprocess.run(
            ["notify-send", "clipboardToPhone send error", message],
            check=False,
            close_fds=True,
        )
    except FileNotFoundError:
        logger.error("notify-send not found; cannot display desktop alert.")
    except Exception as exc:
        logger.error(f"Failed to display desktop alert: {exc}")


def _send_plain_messages(api_url: str, payload_messages: list[str]) -> bool:
    total_messages = len(payload_messages)
    for message_index, payload_message in enumerate(payload_messages, start=1):
        try:
            logger.info(f"Sending message {message_index}/{total_messages} to {api_url}")
            response = requests.post(
                api_url,
                data=payload_message.encode("utf-8"),
                timeout=20,
            )
            logger.info("Sent notification payload.")
        except Exception as request_exception:
            logger.exception(f"Send failed: {request_exception}")
            return False

        if response.status_code != 200:
            response_body_preview = response.text[:400].replace("\n", "\\n")
            logger.error(
                "Failed to send notification. "
                f"HTTP Status Code: {response.status_code}; "
                f"Response: {response_body_preview}"
            )
            return False

    return True


def _resolve_api_url_from_env() -> str | None:
    topic_name = os.getenv("NTFY_SEND_TOPIC")
    if not topic_name:
        logger.error("NTFY_SEND_TOPIC is not set; cannot process queued URL jobs.")
        return None
    return f"https://ntfy.sh/{topic_name}"


def _send_single_url_payload(api_url: str, payload_url: str) -> bool:
    payload_size = len(payload_url.encode("utf-8"))
    if payload_size > MAX_NON_FILE_MESSAGE_BYTES:
        logger.error(
            "URL payload exceeds non-file message limit "
            f"({payload_size}>{MAX_NON_FILE_MESSAGE_BYTES}); aborting."
        )
        _show_desktop_error(
            "A URL payload exceeded the message limit; it remains queued for retry."
        )
        return False
    return _send_plain_messages(api_url, [payload_url])


def _enqueue_and_send_url_jobs(
    lineate, urls: list[str], *, convert: bool
) -> list[str]:
    queue_name = SEND_URL_QUEUE_NAME
    workflow = SEND_CONVERT_WORKFLOW if convert else SEND_RAW_WORKFLOW
    job_payload = {"convert": convert}
    jobs = [
        lineate.persistent_url_queue.create_url_job(
            url,
            workflow=workflow,
            payload=job_payload,
        )
        for url in urls
    ]
    added_count = lineate.persistent_url_queue.enqueue_jobs(queue_name, jobs)
    logger.info(
        f"Queue {queue_name}: enqueued {added_count} new URL(s); requested {len(urls)}."
    )

    def _process_claimed_job(job: dict[str, object]) -> str | None:
        queued_url = job.get("url")
        if not isinstance(queued_url, str) or not queued_url:
            logger.error("Queue job missing non-empty url; refusing to continue.")
            return None
        queued_workflow = job.get("workflow")
        if queued_workflow not in {SEND_RAW_WORKFLOW, SEND_CONVERT_WORKFLOW}:
            logger.error(
                f"Queue job has unsupported workflow {queued_workflow!r}; refusing to continue."
            )
            return None

        api_url = _resolve_api_url_from_env()
        if not api_url:
            return None

        payload_url = queued_url
        if queued_workflow == SEND_CONVERT_WORKFLOW:
            payload_url = lineate.process_url(
                queued_url,
                openInBrowser=False,
                forceConvertAllUrls=True,
                summarise=True,
                forceNoConvert=False,
                forceRefreshAll=False,
            )
            if not payload_url:
                logger.error(f"URL conversion returned no result for {queued_url}.")
                return None

        if not _send_single_url_payload(api_url, payload_url):
            return None
        return payload_url

    delivered_urls, drain_status = lineate.persistent_url_queue.drain_queue(
        queue_name, _process_claimed_job
    )
    if drain_status == "busy":
        logger.info(
            f"Queue {queue_name} is currently claimed by another running process; "
            "this run only enqueued new URLs."
        )
    elif drain_status == "drained_with_failures":
        logger.error(
            f"Queue {queue_name} processed available URLs, "
            "but one or more failed URLs remain queued for retry."
        )
    else:
        logger.info(f"Queue {queue_name}: delivered {len(delivered_urls)} URL(s).")
    return delivered_urls


def _drain_pending_url_jobs(lineate) -> list[str]:
    return _enqueue_and_send_url_jobs(lineate, [], convert=False)


def send_notification_to_phone(topic_name, use_selected_text, *, convert: bool):
    _configure_logging()
    lineate = _load_lineate()
    if use_selected_text:
        text_to_send = get_selected_text()
        if text_to_send is None:
            logger.error("Failed to fetch selected text.")
            return
    else:
        text_to_send = pyperclip.paste()

    _drain_pending_url_jobs(lineate)

    api_url = f"https://ntfy.sh/{topic_name}"
    if not convert:
        urls = lineate.find_urls_in_text(text_to_send)
        is_urls_only = _is_urls_and_whitespace_only(text_to_send, urls)
        if urls and is_urls_only:
            _enqueue_and_send_url_jobs(lineate, urls, convert=False)
            return
        else:
            text_size = len(text_to_send.encode("utf-8"))
            if text_size > MAX_NON_FILE_MESSAGE_BYTES:
                logger.error(
                    "Non-URL content exceeds non-file message limit "
                    f"({text_size}>{MAX_NON_FILE_MESSAGE_BYTES}); aborting."
                )
                _show_desktop_error(
                    "Message too large to send without file attachment. Trim content or send URLs only."
                )
                return
            payload_messages = [text_to_send]
    else:
        lineate.utilities.set_default_summarise(True)
        urls = lineate.find_urls_in_text(text_to_send)
        is_single_link = len(urls) == 1 and text_to_send.strip() == urls[0]
        is_urls_only = _is_urls_and_whitespace_only(text_to_send, urls)
        logger.info(
            f"Detected {len(urls)} url(s); single link: {is_single_link}; urls-only: {is_urls_only}"
        )

        if is_single_link or is_urls_only:
            _enqueue_and_send_url_jobs(lineate, urls, convert=True)
            return
        else:
            gist_url = lineate._process_markdown_text(
                text_to_send, summarise=True, force_refresh=False
            )
            if not gist_url:
                logger.error("Text conversion returned no result.")
                return
            gist_url_size = len(gist_url.encode("utf-8"))
            if gist_url_size > MAX_NON_FILE_MESSAGE_BYTES:
                logger.error(
                    "Non-URL content exceeds non-file message limit "
                    f"({gist_url_size}>{MAX_NON_FILE_MESSAGE_BYTES}); aborting."
                )
                _show_desktop_error(
                    "Message too large to send without file attachment. Trim content or send URLs only."
                )
                return
            payload_messages = [gist_url]

    if _send_plain_messages(api_url, payload_messages):
        logger.info(
            f"Notification sent successfully to {topic_name} in {len(payload_messages)} message(s)."
        )


def main():
    _configure_logging()
    parser = argparse.ArgumentParser(description="Send text as a push notification.")
    parser.add_argument(
        "--selected",
        help="Send selected text instead of clipboard content.",
        action="store_true",
    )
    parser.add_argument(
        "--no-convert",
        help="Send text without converting URLs or creating gists.",
        action="store_true",
    )
    args = parser.parse_args()
    send_notification_to_phone(
        os.getenv("NTFY_SEND_TOPIC"),
        args.selected,
        convert=not args.no_convert,
    )


if __name__ == "__main__":
    main()
