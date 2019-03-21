import json
import logging
import sys

import requests

from lib.parsing import render, recursive_tag
from lib.utils import get_json, dump, diff, get_indexed_data, srdonly

NEW_AUTOMATION = "oldauto" not in sys.argv
VERB_TRANSFORM = {'dispel': 'dispelled', 'discharge': 'discharged'}
SPELL_AUTOMATION_SRC = "https://raw.githubusercontent.com/avrae/avrae-spells/master/spells.json"
IGNORED_FILES = ('3pp', 'stream')

log = logging.getLogger("spells")

if not NEW_AUTOMATION:
    with open('in/auto_spells.json') as f:
        auto_spells = json.load(f)
else:
    auto_spells = requests.get(SPELL_AUTOMATION_SRC).json()

with open('srd/srd-spells.txt') as f:
    srd_spells = [s.strip().lower() for s in f.read().split('\n')]


def get_spells():
    return get_indexed_data('spells/', 'spells.json', 'spell')


def parsetime(spell):
    timedata = spell['time'][0]
    unit = timedata['unit']
    number = timedata['number']
    if unit == 'bonus':
        unit = 'bonus action'
    if number > 1:
        unit = f"{unit}s"
    time = f"{number} {unit}"
    if 'condition' in timedata:
        time = f"{time}, {timedata['condition']}"
    spell['time'] = time
    log.debug(f"{spell['name']} time: {time}")


def plural_to_single(unit):
    return {
        'feet': 'foot'
    }.get(unit, unit.rstrip('s'))


def parserange(spell):
    rangedata = spell['range']
    if rangedata['type'] == 'special':
        range_ = 'Special'
    elif rangedata['type'] == 'point':
        distance = rangedata['distance']
        unit = distance['type']
        if 'amount' in distance:
            if distance['amount'] == 1:
                unit = plural_to_single(unit)
            range_ = f"{distance['amount']} {unit}"
        else:
            range_ = unit.title()
    else:
        distance = rangedata['distance']
        unit = plural_to_single(distance['type'])
        if 'amount' in distance:
            range_ = f"Self ({distance['amount']} {unit} {rangedata['type']})"
        else:
            range_ = f"Self ({unit.title()} {rangedata['type']})"
    spell['range'] = range_
    log.debug(f"{spell['name']} range: {range_}")


def parsecomponents(spell):
    compdata = spell['components']
    v = compdata.get('v')
    s = compdata.get('s')
    m = compdata.get('m')
    if isinstance(m, dict):
        parsedm = f"M ({m['text']})"
    elif isinstance(m, bool):
        parsedm = "M"
    else:
        parsedm = f"M ({m})"

    comps = []
    if v:
        comps.append("V")
    if s:
        comps.append("S")
    if m:
        comps.append(parsedm)
    comps = ', '.join(comps)
    spell['components'] = comps
    log.debug(f"{spell['name']} components: {comps}")


def parseduration(spell):
    durdata = spell['duration'][0]
    concentration = durdata.get('concentration', False)
    if durdata['type'] == 'timed':
        unit = durdata['duration']['type']
        number = durdata['duration']['amount']
        if number > 1:
            unit = f"{unit}s"
        duration = f"{number} {unit}"
        if concentration:
            duration = f"Concentration, up to {duration}"
        elif durdata['duration'].get('upTo'):
            duration = f"Up to {duration}"
    elif durdata['type'] == 'permanent':
        duration = f"Until {' or '.join(VERB_TRANSFORM.get(v, v + 'ed') for v in durdata['ends'])}"
    elif durdata['type'] == 'instant':
        duration = "Instantaneous"
    else:
        duration = durdata['type'].title()

    spell['duration'] = duration
    spell['concentration'] = concentration
    log.debug(f"{spell['name']} duration: {duration}")
    log.debug(f"{spell['name']} concentration: {concentration}")


def parseclasses(spell):
    classes = [c['name'] for c in spell['classes']['fromClassList']]
    subclasses = []
    for subclass in spell['classes'].get('fromSubclass', []):
        if '(' in subclass['class']['name'] or '(' in subclass['subclass']['name']:
            continue
        if subclass['class']['name'] in classes:
            continue
        subclasses.append(f"{subclass['class']['name']} ({subclass['subclass']['name']})")
    classes = list(set(classes))
    subclasses = list(set(subclasses))
    spell['classes'] = sorted(classes)
    spell['subclasses'] = sorted(subclasses)
    log.debug(f"{spell['name']} classes: {classes}")
    log.debug(f"{spell['name']} subclasses: {subclasses}")


def srdfilter(spell):
    if spell['name'].lower() in srd_spells:
        spell['srd'] = True
    else:
        spell['srd'] = False
    log.debug(f"{spell['name']} srd: {spell['srd']}")


def get_automation(spell):
    try:
        auto_spell = next(s for s in auto_spells if s['name'] == spell['name'])
    except StopIteration:
        log.warning("No new automation found!")
        return None
    log.debug(f"Found new automation!")
    return auto_spell['automation']


def get_automation_from_old(spell):
    try:
        auto_spell = next(s for s in auto_spells if s['name'] == spell['name'])
    except StopIteration:
        log.debug("No old automation found.")
        return None

    automation = []
    type_ = auto_spell.get('type')
    if type_ == 'save':
        savedata = auto_spell['save']
        save = savedata['save'][:3].lower()
        damage = savedata['damage']
        higher = auto_spell.get("higher_levels", {})
        data = {
            "type": "target",
            "target": "all",
            "effects": [
                {
                    "type": "save",
                    "stat": save,
                    "fail": [],
                    "success": []
                }
            ]
        }
        if damage:
            data['meta'] = [
                {
                    "type": "roll",
                    "dice": damage,
                    "name": "damage",
                    "higher": higher
                }
            ]
            if auto_spell.get('scales', True) and auto_spell['level'] == '0':
                data['meta'][0]['cantripScale'] = True
            data['effects'][0]['fail'].append({
                "type": "damage",
                "damage": "{damage}"
            })
            if savedata['success'] == 'half':
                data['effects'][0]['success'].append({
                    "type": "damage",
                    "damage": "{damage}/2"
                })
    elif type_ == 'attack':
        damage = auto_spell['atk']['damage']
        higher = auto_spell.get("higher_levels", {})
        data = {
            "type": "target",
            "target": "each",
            "effects": [
                {
                    "type": "attack",
                    "hit": [
                        {
                            "type": "damage",
                            "damage": damage,
                            "higher": higher
                        }
                    ],
                    "miss": []
                }
            ]
        }
        if auto_spell.get('scales', True) and auto_spell['level'] == '0':
            data['effects'][0]['hit'][0]['cantripScale'] = True
    else:
        damage = auto_spell['damage']
        higher = auto_spell.get("higher_levels", {})
        data = {
            "type": "target",
            "target": "each",
            "effects": [
                {
                    "type": "damage",
                    "damage": damage,
                    "higher": higher
                }
            ]
        }
    automation.append(data)
    automation.append({
        "type": "text",
        "text": spell_context(auto_spell).strip()
    })
    return automation


def spell_context(spell):
    """:returns str - Spell context."""
    context = ""

    if spell['type'] == 'save':  # context!
        if isinstance(spell['text'], list):
            text = '\n'.join(spell['text'])
        else:
            text = spell['text']
        sentences = text.split('.')

        for i, s in enumerate(sentences):
            if spell.get('save', {}).get('save').lower() + " saving throw" in s.lower():
                _sent = []
                for sentence in sentences[i:i + 3]:
                    if not '\n\n' in sentence:
                        _sent.append(sentence)
                    else:
                        break
                _ctx = '. '.join(_sent)
                if not _ctx.strip() in context:
                    context += f'{_ctx.strip()}.\n'
    elif spell['type'] == 'attack':
        if isinstance(spell['text'], list):
            text = '\n'.join(spell['text'])
        else:
            text = spell['text']
        sentences = text.split('.')

        for i, s in enumerate(sentences):
            if " spell attack" in s.lower():
                _sent = []
                for sentence in sentences[i:i + 3]:
                    if not '\n\n' in sentence:
                        _sent.append(sentence)
                    else:
                        break
                _ctx = '. '.join(_sent)
                if not _ctx.strip() in context:
                    context += f'{_ctx.strip()}.\n'
    else:
        if 'short' in spell:
            context = spell['short']

    return context


def ensure_ml_order(spells, srd=False):
    log.info("Attempting to put spells in ML order...")
    try:
        with open(f'in/map-{"srd-" if srd else ""}spell.json') as f:
            spell_map_dict = json.load(f)
    except FileNotFoundError:
        log.warning(f"ML spell map not found. Spell order may not match ML outputs.")
        return spells
    spell_map = sorted(((int(i), name) for i, name in spell_map_dict.items()), key=lambda i: i[0])
    spell_map = [s[1] for s in spell_map]  # index holds position, since one-hot

    # sort spells in map first, then map position, then name
    def spellsort(s):
        try:
            ml_index = spell_map.index(s['name'])
        except ValueError:
            ml_index = -1
        return s['name'] not in spell_map, ml_index, s['name']

    spells = sorted(spells, key=spellsort)
    if len(spells) != len(spell_map):
        log.warning(f"Number of spells differs from spell map length. Delta: {len(spells) - len(spell_map)}")
    return spells


def parse(data):
    processed = []
    for spell in data:
        log.info(f"Parsing {spell['name']}...")
        parsetime(spell)
        parserange(spell)
        parsecomponents(spell)
        parseduration(spell)
        parseclasses(spell)
        srdfilter(spell)

        ritual = spell.get('meta', {}).get('ritual', False)
        desc = render(spell['entries'])
        if 'entriesHigherLevel' in spell:
            higherlevels = render(spell['entriesHigherLevel']) \
                .replace("**At Higher Levels**: ", "")
        else:
            higherlevels = None

        if NEW_AUTOMATION:
            automation = get_automation(spell)
        else:
            automation = get_automation_from_old(spell)

        newspell = {
            "name": spell['name'],
            "level": spell['level'],
            "school": spell['school'],
            "casttime": spell['time'],
            "range": spell['range'],
            "components": spell['components'],
            "duration": spell['duration'],
            "description": desc,
            "classes": spell['classes'],
            "subclasses": spell['subclasses'],
            "ritual": ritual,
            "higherlevels": higherlevels,
            "source": spell['source'],
            "page": spell.get('page', '?'),
            "concentration": spell['concentration'],
            "automation": automation,
            "srd": spell['srd']
        }
        processed.append(recursive_tag(newspell))

    processed = ensure_ml_order(processed)
    return processed


def get_auto_only(data):
    return [{
        "name": spell['name'],
        "automation": spell['automation']
    } for spell in data]


def site_parse(data):
    out = []
    for spell in data:
        if not spell['srd']:
            continue
        spell['classes'] = ', '.join(spell['classes'])
        spell['subclasses'] = ', '.join(spell['subclasses'])
        spell['components'] = site_parse_components(spell['components'])
        if spell['duration'].startswith("Concentration, up to "):
            spell['duration'] = spell['duration'][len("Concentration, up to "):]
        del spell['srd'], spell['source'], spell['page']
        out.append(spell)
    return out


def site_parse_components(components):
    out = {"verbal": False, "somatic": False, "material": ""}
    components = components.split(", ")
    if 'V' in components:
        out['verbal'] = True
    if 'S' in components:
        out['somatic'] = True
    m = next((c for c in components if c.startswith('M')), None)
    if m:
        out['material'] = m[3:-1]
    return out


def run():
    data = get_spells()
    processed = parse(data)
    dump(processed, 'spells.json')
    srd = ensure_ml_order(srdonly(processed), True)
    dump(srd, 'srd-spells.json')
    diff('srd-spells.json')
    dump(get_auto_only(processed), 'spellauto.json')

    site_templates = site_parse(processed)
    dump(site_templates, 'template-spells.json')


if __name__ == '__main__':
    run()
