import json
import logging
import os
import sys
import time

import requests

DATA_SRC = "https://5etools.com/data/"
LOGLEVEL = logging.INFO if not "debug" in sys.argv else logging.DEBUG

log_formatter = logging.Formatter('%(levelname)s:%(name)s: %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.setLevel(LOGLEVEL)
logger.addHandler(handler)
log = logging.getLogger(__name__)


def get_json(path):
    log.info(f"Getting {path}...")
    return requests.get(DATA_SRC + path).json()


def get_data(path):
    try:
        with open(f'cache/{path}') as f:
            dat = json.load(f)
            log.info(f"Loaded {path} from cache")
    except FileNotFoundError:
        dat = get_json(path)
        with open(f'cache/{path}', 'w') as f:
            json.dump(dat, f, indent=2)
    return dat


def dump(data, filename):
    try:
        os.rename(f'out/{filename}', f'bak/{int(time.time())}-{filename}')
    except FileNotFoundError:
        pass
    with open(f'out/{filename}', 'w') as f:
        json.dump(data, f, indent=2)


def nth_repl(s, sub, repl, nth):
    find = s.find(sub)
    # if find is not p1 we have found at least one match for the substring
    i = find != -1
    # loop util we find the nth or we find no match
    while find != -1 and i != nth:
        # find + 1 means we start at the last match start index + 1
        find = s.find(sub, find + 1)
        i += 1
    # if i  is equal to nth we found nth matches so replace
    if i == nth:
        return s[:find] + repl + s[find + len(sub):]
    return s


def explicit_sources(data, sources):
    for entry in data:
        if entry['source'] in sources:
            new_name = f"{entry['name']} ({entry['source']})"
            log.info(f"Renaming {entry['name']} to {new_name} (explicit override)")
            entry['name'] = new_name
    return data


def fix_dupes(data, source_hierarchy):
    for entry in data:
        if len([r for r in data if r['name'] == entry['name']]) > 1:
            log.warning(f"Found duplicate: {entry['name']}")
            hierarchied = sorted([r for r in data if r['name'] == entry['name']],
                                 key=lambda r: source_hierarchy.index(
                                     next((s for s in source_hierarchy if s in r['source']), 'nil')))
            for r in hierarchied[1:]:
                new_name = f"{r['name']} ({r['source']})"
                log.info(f"Renaming {r['name']} to {new_name}")
                r['name'] = new_name
    return data


def remove_ignored(data, ignored_sources):
    for entry in data.copy():
        if entry['source'] in ignored_sources:
            data.remove(entry)
            log.info(f"{entry['name']} ({entry['source']}) ignored, removing!")
    return data
