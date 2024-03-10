import os
import subprocess
import re
from urllib.parse import urlparse
import sys
from util import *

sys.path.append(getConfig()["convertLinksDir"])
from convertLinks import main

# Fetch data from environment variable
data = "https://gist.github.com/0001c2617fd8c2729746ca032129f312"  # os.environ.get("message", "")

print("it worked", data)


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


# Copy to clipboard
copy_to_clipboard(data)


sys.path.append("/home/pimania/dev/convertLinks")
from convertLinks import main

main(data, True, False)
