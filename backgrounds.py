import logging

from lib.parsing import render
from lib.utils import get_data, dump, diff

log = logging.getLogger("backgrounds")

SRD = ['Acolyte']
PROF_KEYS = ("skillProficiencies", "languageProficiencies", "toolProficiencies")


def get_latest_backgrounds():
    return get_data("backgrounds.json")['background']


def parse_profs(raw):
    profs = {}
    for proftype in PROF_KEYS:
        profname = proftype[:-13]
        if proftype in raw:
            profs[profname] = []
            for prof in raw[proftype]:
                if 'choose' in prof:
                    profs[profname].append(' or '.join(p for p in prof['choose']['from']))
                elif 'any' in prof:
                    profs[profname].append(f"any {prof['any']} {profname}{'s' if prof['any'] > 1 else ''}")
                else:
                    profs[profname].extend(k for k in prof.keys())
    return profs


def parse_traits(raw):
    traits = []
    for entry in raw['entries']:
        if entry['type'] == 'list':
            for item in entry['items']:
                trait = {
                    'name': item['name'],
                    'text': render(item.get('entry') or item.get('entries'))
                }
                traits.append(trait)
        elif entry['type'] in ('entries', 'section'):
            trait = {
                'name': entry['name'],
                'text': render(entry['entries'])
            }
            traits.append(trait)
        else:
            log.warning(f"Unknown entry: {entry}")
            continue
    return traits


def parse(data):
    out = []
    for raw in data:
        log.info(f"Parsing {raw['name']}...")
        profs = parse_profs(raw)
        traits = parse_traits(raw)

        background = {
            "name": raw['name'],
            "proficiencies": profs,
            "traits": traits,
            "source": raw['source'],
            "page": raw.get('page', '?')
        }
        out.append(background)
    return out


def srdfilter(data):
    for background in data:
        if background['name'] in SRD:
            background['srd'] = True
        else:
            background['srd'] = False
    return data


def run():
    data = get_latest_backgrounds()
    data = parse(data)
    data = srdfilter(data)
    dump(data, 'backgrounds.json')
    diff('backgrounds.json')


if __name__ == '__main__':
    run()
