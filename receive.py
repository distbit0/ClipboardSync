import argparse
import subprocess
from urllib.parse import urlparse

# Argument parsing setup
parser = argparse.ArgumentParser(
    description="Copy data to clipboard and open URLs in Brave browser."
)
parser.add_argument(
    "data",
    type=str,
    help="The string data to copy to clipboard and/or open in Brave if it's a URL.",
)
args = parser.parse_args()

# Fetch data from parsed arguments
data = args.data

# Specify the Brave browser path
brave_path = "/usr/bin/brave-browser-stable"


def is_url(s):
    try:
        result = urlparse(s)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def open_in_brave(url):
    subprocess.run([brave_path, url])


def copy_to_clipboard(input_string):
    process = subprocess.Popen(
        ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, close_fds=True
    )
    process.communicate(input=input_string.encode("utf-8"))


# Copy to clipboard
copy_to_clipboard(data)

# Open in Brave if it's a URL
if is_url(data):
    open_in_brave(data)
