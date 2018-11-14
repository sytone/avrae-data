import logging

from lib.utils import get_data, dump, fix_dupes

log = logging.getLogger("feats")

SOURCE_HIERARCHY = ('XGE', 'PHB', 'UA', 'nil')


def get_latest_feats():
    return get_data("feats.json")['feat']


def srdfilter(data):
    for feat in data:
        if feat['name'].lower() == 'grappler':
            feat['srd'] = True
        else:
            feat['srd'] = False
    return data


def run():
    data = get_latest_feats()
    data = srdfilter(data)
    data = fix_dupes(data, SOURCE_HIERARCHY, True)
    dump(data, 'feats.json')


if __name__ == '__main__':
    run()
