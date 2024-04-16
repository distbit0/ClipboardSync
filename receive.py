import os
import time
import subprocess
import re
import json
import threading
from urllib.parse import urlparse
import sys
from util import *
import requests
import websocket
import pysnooper
from dotenv import load_dotenv

sys.path.append(getConfig()["convertLinksDir"])
from convertLinks import main

load_dotenv()


# @pysnooper.snoop()
def copy_to_clipboard(input_string):
    process = subprocess.Popen(
        ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, close_fds=True
    )
    process.communicate(input=input_string.encode())
    return


def find_urls_in_text(text):
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )
    return url_pattern.findall(text)


# @pysnooper.snoop()
def on_message(ws, message):
    data = json.loads(message)
    if "message" in data:
        message_data = data["message"]
        print("new message: " + message_data)
        if message_data == "You received a file: attachment.txt":
            id = data.get("id", "")
            print("id: " + id)
            if not id:
                message_data = "No attachment found."
            else:
                attachmentUrl = "https://ntfy.sh/file/" + id + ".txt"
                message_data = requests.get(attachmentUrl).text
                print("attachmentUrl: " + attachmentUrl)
                print("message_data from attachmentUrl: " + message_data)
        copy_to_clipboard(message_data)
        main(message_data, True, False)


def on_error(ws, error):
    print(f"WebSocket error: {error}")


def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")


def on_open(ws):
    print("WebSocket connection opened")


def lfg():
    topic = os.getenv("NTFY_RECEIVE_TOPIC")
    if not topic:
        print("Topic name not found in .env file. Please set the NTFY_TOPIC variable.")
        sys.exit(1)

    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        f"wss://ntfy.sh/{topic}/ws",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.on_open = on_open
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        ws.close()


if __name__ == "__main__":
    lfg()
