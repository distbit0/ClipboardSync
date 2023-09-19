import requests
import pyperclip
import argparse


def send_notification_to_phone(topic_name):
    clipboard_content = pyperclip.paste()
    api_url = f"http://ntfy.sh/{topic_name}"

    try:
        response = requests.post(api_url, data=clipboard_content)
        if response.status_code == 200:
            print(f"Notification sent successfully to {topic_name}.")
        else:
            print(
                f"Failed to send notification. HTTP Status Code: {response.status_code}"
            )
    except Exception as request_exception:
        print(f"An exception occurred: {request_exception}")


def main():
    parser = argparse.ArgumentParser(
        description="Send clipboard contents as a push notification."
    )
    parser.add_argument("topic_name", help="The topic name for the push notification.")

    args = parser.parse_args()
    send_notification_to_phone(args.topic_name)


if __name__ == "__main__":
    main()
