import os
import subprocess
import re
from urllib.parse import urlparse

# Fetch data from environment variable
data = os.environ.get("message", "")

print("it worked", data)

# Specify the Brave browser path
brave_path = "/usr/bin/brave-browser-stable"


def open_in_brave(url):
    subprocess.run([brave_path, url])


def find_urls_in_text(text):
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )
    return url_pattern.findall(text)


def openUrlsInData(data):
    urls_to_open = find_urls_in_text(data)
    for url in urls_to_open:
        open_in_brave(url)


def copy_to_clipboard(input_string):
    process = subprocess.Popen(
        ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, close_fds=True
    )
    process.communicate(input=input_string.encode("utf-8"))


# Copy to clipboard
copy_to_clipboard(data)

# Open URLs in data in Brave
openUrlsInData(data)
