import os
import subprocess
import re
from urllib.parse import urlparse
import sys
from util import *
import requests

sys.path.append(getConfig()["convertLinksDir"])
from convertLinks import main


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


# Fetch data from environment variable
data = os.environ.get("message", "")
if data == "You received a file: attachment.txt":
    id = os.environ.get("id", "")
    if not id:
        data = "No attachment found."
    else:
        attachmentUrl = "https://ntfy.sh/file/" + id + ".txt"
        data = requests.get(attachmentUrl).text

print("it worked", data)
copy_to_clipboard(data)
main(data, True, False)
