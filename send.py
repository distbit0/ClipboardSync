import requests
import pyperclip
import argparse
import subprocess


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
        text_to_send = get_selected_text()
        if text_to_send is None:
            print("Failed to fetch selected text.")
            return
    else:
        text_to_send = pyperclip.paste()

    api_url = f"http://ntfy.sh/{topic_name}"

    try:
        response = requests.post(api_url, data=text_to_send)
        if response.status_code == 200:
            print(f"Notification sent successfully to {topic_name}.")
        else:
            print(
                f"Failed to send notification. HTTP Status Code: {response.status_code}"
            )
    except Exception as request_exception:
        print(f"An exception occurred: {request_exception}")


def main():
    parser = argparse.ArgumentParser(description="Send text as a push notification.")
    parser.add_argument("topic_name", help="The topic name for the push notification.")
    parser.add_argument(
        "--selected",
        help="Send selected text instead of clipboard content.",
        action="store_true",
    )

    args = parser.parse_args()
    send_notification_to_phone(args.topic_name, use_selected_text=args.selected)


if __name__ == "__main__":
    main()
