import logging

from lib.parsing import render, ABILITY_MAP
from lib.utils import get_data, dump, fix_dupes, diff, english_join, srdonly

log = logging.getLogger("feats")

SOURCE_HIERARCHY = ('XGE', 'PHB', 'UA', 'nil')


def get_latest_feats():
    return get_data("feats.json")['feat']


def parse_prereq(feat):
    prereq = []

    if 'prerequisite' in feat:
        for entry in feat['prerequisite']:
            if 'race' in entry:
                prereq.append(english_join(
                    f"{r['name']}" + (f" ({r['subrace']})" if 'subrace' in r else '') for r in entry['race']))
            if 'ability' in entry:
                abilities = []
                for ab in entry['ability']:
                    abilities.extend(f"{ABILITY_MAP.get(a)} {s}" for a, s in ab.items())
                prereq.append(english_join(abilities))
            if 'spellcasting' in entry:
                prereq.append("The ability to cast at least one spell")
            if 'proficiency' in entry:
                prereq.append(f"Proficiency with {entry['proficiency'][0]['armor']} armor")
            if 'level' in entry:
                prereq.append(f"Level {entry['level']}")
            if 'special' in entry:
                prereq.append(entry['special'])

    if prereq:
        return '\n'.join(prereq)
    return None


def parse_ability(feat):
    ability = None
    if 'ability' in feat:
        if 'choose' in feat['ability']:
            ability = english_join(ABILITY_MAP.get(a) for a in feat['ability']['choose'][0]['from'])
        else:
            ability = english_join(ABILITY_MAP.get(a) for a in feat['ability'].keys())
    return ability


def prerender(data):
    out = []
    for feat in data:
        log.debug(feat['name'])
        desc = render(feat['entries'])
        prereq = parse_prereq(feat)
        ability = parse_ability(feat)

        new_feat = {
            "name": feat['name'],
            "prerequisite": prereq,
            "source": feat['source'],
            "page": feat['page'],
            "desc": desc,
            "ability": ability
        }
        out.append(new_feat)
    return out


def srdfilter(data):
    for feat in data:
        if feat['name'].lower() == 'grappler':
            feat['srd'] = True
        else:
            feat['srd'] = False
    return data


def run():
    data = get_latest_feats()
    data = prerender(data)
    data = srdfilter(data)
    data = fix_dupes(data, SOURCE_HIERARCHY, True)
    dump(data, 'feats.json')
    dump(srdonly(data), 'srd-feats.json')
    diff('srd-feats.json')


if __name__ == '__main__':
    run()
