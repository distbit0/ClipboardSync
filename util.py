import os
import json


def getAbsPath(path):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), path))


def getConfig():
    return json.load(open(getAbsPath("config.json")))
