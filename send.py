import argparse
import io
import os
import subprocess
import sys

import pyperclip
import requests
from dotenv import load_dotenv
from loguru import logger

from util import getConfig

sys.path.append(getConfig()["convertLinksDir"])
import lineate

load_dotenv()

logger.remove()
logger.add("send.log", rotation="30 KB", retention=5, enqueue=True)
logger.add(sys.stdout, level="INFO")


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


def convert_links_in_text(
    text,
):
    lineate.utilities.set_default_summarise(True)
    urls = lineate.find_urls_in_text(text)
    if not urls:
        return text, []

    converted_pairs = []
    for url in urls:
        converted_url = lineate.process_url(
            url,
            openInBrowser=False,
            forceConvertAllUrls=True,
            summarise=True,
            forceNoConvert=False,
            forceRefreshAll=False,
        )
        converted_pairs.append((url, converted_url))

    updated_text = text
    for original_url, converted_url in converted_pairs:
        if converted_url and converted_url != original_url:
            updated_text = updated_text.replace(original_url, converted_url)

    return updated_text, [converted for _, converted in converted_pairs if converted]


def send_notification_to_phone(topic_name, use_selected_text):
    if use_selected_text:
        text_to_send = get_selected_text()
        if text_to_send is None:
            logger.error("Failed to fetch selected text.")
            return
    else:
        text_to_send = pyperclip.paste()

    api_url = f"http://ntfy.sh/{topic_name}"
    headers = {}
    urls = lineate.find_urls_in_text(text_to_send)
    is_single_link = len(urls) == 1 and text_to_send.strip() == urls[0]
    logger.info(f"Detected {len(urls)} url(s); single link: {is_single_link}")

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
    else:
        text_to_send, converted_urls = convert_links_in_text(
            text_to_send,
            openInBrowser=False,
            forceConvertAllUrls=True,
            summarise=True,
            forceNoConvert=False,
            forceRefreshAll=False,
        )
        logger.info(f"Converted {len(converted_urls)} url(s) for attachment.")
        # Convert the text into a byte stream
        file_like_object = io.BytesIO(text_to_send.encode("utf-8"))
        file_like_object.name = "message.txt"  # Define a filename for the attachment

        # Adjust the headers to include the filename, indicating an attachment
        headers["X-Filename"] = "message.txt"
        dataToSend = file_like_object

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
    parser = argparse.ArgumentParser(description="Send text as a push notification.")
    parser.add_argument(
        "--selected",
        help="Send selected text instead of clipboard content.",
        action="store_true",
    )
    args = parser.parse_args()
    send_notification_to_phone(
        os.getenv("NTFY_SEND_TOPIC"),
        args.selected,
    )


if __name__ == "__main__":
    main()
