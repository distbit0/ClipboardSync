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


def copy_to_clipboard(input_string):
    subprocess.Popen(
        ["xclip", "-selection", "clipboard"],
        stdin=subprocess.PIPE,
        universal_newlines=True,
    ).stdin.write(input_string)


def find_urls_in_text(text):
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )
    return url_pattern.findall(text)


def on_message(ws, message):
    data = json.loads(message)
    if "message" in data:
        message_data = data["message"]
        if message_data == "You received a file: attachment.txt":
            id = data.get("id", "")
            if not id:
                message_data = "No attachment found."
            else:
                attachmentUrl = "https://ntfy.sh/file/" + id + ".txt"
                message_data = requests.get(attachmentUrl).text
        copy_to_clipboard(message_data)
        main(message_data, True, False)


def on_error(ws, error):
    print(f"WebSocket error: {error}")


def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")


def on_open(ws):
    print("WebSocket connection opened")


# @pysnooper.snoop()
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
