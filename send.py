import requests
import pyperclip
import argparse
import subprocess
import io
from urllib.parse import urlparse
import sys
from util import *

sys.path.append(getConfig()["convertLinksDir"])
from convertLinks import main as convertLinks


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


def send_notification_to_phone(topic_name, use_selected_text=False):
    if use_selected_text:
        text_to_send = (
            get_selected_text()
        )  # This function needs to be defined elsewhere
        if text_to_send is None:
            print("Failed to fetch selected text.")
            return
    else:
        text_to_send = pyperclip.paste()

    api_url = f"http://ntfy.sh/{topic_name}"
    headers = {}
    textIsSingleLink = (
        urlparse(text_to_send).netloc != "" and text_to_send.count("http") == 1
    )
    if not textIsSingleLink:
        # Convert the text into a byte stream
        file_like_object = io.BytesIO(text_to_send.encode("utf-8"))
        file_like_object.name = "message.txt"  # Define a filename for the attachment

        # Adjust the headers to include the filename, indicating an attachment
        headers["X-Filename"] = "message.txt"
        dataToSend = file_like_object
    else:
        if "READ" in topic_name:
            text_to_send = convertLinks(text_to_send, False, True)[0]
        else:
            text_to_send = convertLinks(text_to_send, False, False)[0]
        dataToSend = text_to_send.encode("utf-8")

    try:
        print(f"Sending {dataToSend} to {api_url}")
        response = requests.post(api_url, data=dataToSend, headers=headers)
    except Exception as request_exception:
        print(f"An exception occurred: {request_exception}")
        return

    # Check the response status for both attachment and non-attachment cases
    if response.status_code == 200:
        print(f"Notification sent successfully to {topic_name}.")
    else:
        print(f"Failed to send notification. HTTP Status Code: {response.status_code}")


def main():
    parser = argparse.ArgumentParser(description="Send text as a push notification.")
    parser.add_argument("topic_name", help="The topic name for the push notification.")
    parser.add_argument(
        "--selected",
        help="Send selected text instead of clipboard content.",
        action="store_true",
    )

    args = parser.parse_args()
    send_notification_to_phone(
        args.topic_name,
        use_selected_text=args.selected,
    )


if __name__ == "__main__":
    main()
