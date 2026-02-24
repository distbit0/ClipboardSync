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


def convert_links_in_text(text):
    lineate = _load_lineate()
    urls = lineate.find_urls_in_text(text)
    if not urls:
        return text, []
    if not _is_urls_and_whitespace_only(text, urls):
        return text, []

    converted_urls = lineate.main(
        text,
        openInBrowser=False,
        forceConvertAllUrls=True,
        summarise=True,
        forceNoConvert=False,
        forceRefreshAll=False,
    )
    if not converted_urls:
        return "", []

    converted_text = "\n".join(converted_urls)
    return converted_text, converted_urls


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


def _split_urls_into_messages(urls: list[str], max_message_bytes: int) -> list[str]:
    messages: list[str] = []
    current_urls: list[str] = []
    current_size = 0

    for url in urls:
        separator_size = 1 if current_urls else 0
        url_size = len(url.encode("utf-8"))
        entry_size = separator_size + url_size

        if url_size > max_message_bytes:
            raise ValueError("A single URL exceeds the non-file message limit.")

        if current_size + entry_size <= max_message_bytes:
            current_urls.append(url)
            current_size += entry_size
            continue

        messages.append("\n".join(current_urls))
        current_urls = [url]
        current_size = url_size

    if current_urls:
        messages.append("\n".join(current_urls))

    return messages


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

    api_url = f"https://ntfy.sh/{topic_name}"
    if not convert:
        urls = lineate.find_urls_in_text(text_to_send)
        is_urls_only = _is_urls_and_whitespace_only(text_to_send, urls)
        if urls and is_urls_only:
            try:
                payload_messages = _split_urls_into_messages(
                    urls,
                    MAX_NON_FILE_MESSAGE_BYTES,
                )
            except ValueError as split_error:
                logger.error(f"Could not split URL payload: {split_error}")
                return
            logger.info(f"Split URL payload into {len(payload_messages)} message chunk(s).")
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

        if is_single_link:
            text_to_send = lineate.process_url(
                urls[0],
                openInBrowser=False,
                forceConvertAllUrls=True,
                summarise=True,
                forceNoConvert=False,
                forceRefreshAll=False,
            )
            if not text_to_send:
                logger.error("Single-link conversion returned no result.")
                return
            try:
                payload_messages = _split_urls_into_messages(
                    [text_to_send],
                    MAX_NON_FILE_MESSAGE_BYTES,
                )
            except ValueError as split_error:
                logger.error(f"Could not split URL payload: {split_error}")
                return
        elif is_urls_only:
            _converted_text, converted_urls = convert_links_in_text(
                text_to_send,
            )
            if not converted_urls:
                logger.error("URL conversion returned no results; aborting send.")
                return
            try:
                payload_messages = _split_urls_into_messages(
                    converted_urls,
                    MAX_NON_FILE_MESSAGE_BYTES,
                )
            except ValueError as split_error:
                logger.error(f"Could not split URL payload: {split_error}")
                return
            logger.info(
                f"Converted {len(converted_urls)} url(s) into {len(payload_messages)} message chunk(s)."
            )
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
