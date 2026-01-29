import argparse
import io
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


def _build_attachment_payload(text: str, headers: dict) -> io.BytesIO:
    file_like_object = io.BytesIO(text.encode("utf-8"))
    file_like_object.name = "message.txt"
    headers["X-Filename"] = "message.txt"
    return file_like_object


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

    api_url = f"http://ntfy.sh/{topic_name}"
    headers = {}
    if not convert:
        dataToSend = _build_attachment_payload(text_to_send, headers)
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
            dataToSend = text_to_send.encode("utf-8")
        elif is_urls_only:
            text_to_send, converted_urls = convert_links_in_text(
                text_to_send,
            )
            if not converted_urls:
                logger.error("URL conversion returned no results; aborting send.")
                return
            logger.info(f"Converted {len(converted_urls)} url(s) for attachment.")
            dataToSend = _build_attachment_payload(text_to_send, headers)
        else:
            gist_url = lineate._process_markdown_text(
                text_to_send, summarise=True, force_refresh=False
            )
            if not gist_url:
                logger.error("Text conversion returned no result.")
                return
            dataToSend = gist_url.encode("utf-8")

    try:
        logger.info(f"Sending to {api_url} with headers {headers}")
        response = requests.post(api_url, data=dataToSend, headers=headers)
        logger.info("Sent notification payload.")
    except Exception as request_exception:
        logger.exception(f"Send failed: {request_exception}")
        return

    # Check the response status for both attachment and non-attachment cases
    if response.status_code == 200:
        logger.info(f"Notification sent successfully to {topic_name}.")
    else:
        logger.error(
            f"Failed to send notification. HTTP Status Code: {response.status_code}"
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
