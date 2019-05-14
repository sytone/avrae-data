import difflib
import json
import logging
import os
import sys

import requests

DATA_SRC = os.environ.get("DATA_SRC")
LOGLEVEL = logging.INFO if "debug" not in sys.argv else logging.DEBUG

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
        if "nocache" not in sys.argv:
            with open(f'cache/{path}') as f:
                dat = json.load(f)
                log.info(f"Loaded {path} from cache")
        else:
            raise FileNotFoundError  # I mean.
    except FileNotFoundError:
        dat = get_json(path)
        with open(f'cache/{path}', 'w') as f:
            json.dump(dat, f, indent=2)
    return dat


def get_indexed_data(root, cache_name, root_key):
    try:
        if "nocache" not in sys.argv:
            with open(f'cache/{cache_name}') as f:
                cached = json.load(f)
                log.info(f"Loaded {cache_name} data from cache")
                return cached
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        index = get_json(f'{root}index.json')
        out = []
        for src, file in index.items():
            if '3pp' in src or 'Stream' in src:
                log.info(f"Skipped {file}: {src}")
                continue
            data = get_json(f"{root}{file}")
            out.extend(data[root_key])
            log.info(f"  Processed {file}: {len(data[root_key])} entries")
        with open(f'cache/{cache_name}', 'w') as f:
            json.dump(out, f, indent=2)
        return out


def dump(data, filename):
    try:
        os.rename(f'out/{filename}', f'bak/{filename}.old')
    except FileNotFoundError:
        pass
    with open(f'out/{filename}', 'w') as f:
        json.dump(data, f, indent=2)


def diff(filename):
    try:
        with open(f'bak/{filename}.old') as before:
            old = before.readlines()
        with open(f'out/{filename}') as after:
            new = after.readlines()
    except FileNotFoundError:
        return
    sys.stdout.writelines(difflib.unified_diff(old, new, fromfile=f"bak/{filename}.old", tofile=f"out/{filename}"))


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


def fix_dupes(data, source_hierarchy, remove_dupes=False):
    for entry in data.copy():
        if len([r for r in data if r['name'] == entry['name']]) > 1:
            log.warning(f"Found duplicate: {entry['name']}")
            hierarchied = sorted([r for r in data if r['name'] == entry['name']],
                                 key=lambda r: source_hierarchy.index(
                                     next((s for s in source_hierarchy if s in r['source']), 'nil')))
            for r in hierarchied[1:]:
                if not remove_dupes:
                    new_name = f"{r['name']} ({r['source']})"
                    log.info(f"Renaming {r['name']} to {new_name}")
                    r['name'] = new_name
                else:
                    log.info(f"Removing {r['name']} ({r['source']})")
                    data.remove(r)
    return data


def remove_ignored(data, ignored_sources):
    for entry in data.copy():
        if entry['source'] in ignored_sources:
            data.remove(entry)
            log.info(f"{entry['name']} ({entry['source']}) ignored, removing!")
    return data


def english_join(l):
    l = list(l)
    if len(l) < 2:
        return l[0]
    elif len(l) == 2:
        return ' or '.join(l)
    else:
        return ', '.join(l[:-1]) + f', or {l[-1]}'


def srdonly(data):
    return [b for b in data if b['srd']]
