import logging

from utils import get_data, dump

log = logging.getLogger("feats")


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
    dump(data, 'feats.json')


if __name__ == '__main__':
    run()
