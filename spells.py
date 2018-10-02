import json
import logging

from utils import get_json, render, recursive_tag

VERB_TRANSFORM = {'dispel': 'dispelled', 'discharge': 'discharged'}

log = logging.getLogger("spells")

with open('other/auto_spells.json') as f:
    auto_spells = json.load(f)


def get_spells():
    try:
        with open('cache/spells.json') as f:
            spells = json.load(f)
            log.info("Loaded spell data from cache")
    except FileNotFoundError:
        index = get_json('spells/index.json')
        spells = []
        for src, file in index.items():
            if '3pp' in src:
                continue
            data = get_json(f"spells/{file}")
            spells.extend(data['spell'])
            log.info(f"  Processed {file}: {len(data['spell'])} spells")
        with open('cache/spells.json', 'w') as f:
            json.dump(spells, f, indent=2)
    return spells


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


def parserange(spell):
    rangedata = spell['range']
    if rangedata['type'] != 'special':
        distance = rangedata['distance']
        unit = distance['type']
        if 'amount' in distance:
            range_ = f"{distance['amount']} {unit}"
        else:
            range_ = unit.title()
    else:
        range_ = 'Special'
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
    spell['classes'] = classes
    spell['subclasses'] = subclasses
    log.debug(f"{spell['name']} classes: {classes}")
    log.debug(f"{spell['name']} subclasses: {subclasses}")


def get_automation(spell):
    try:
        auto_spell = next(s for s in auto_spells if s['name'] == spell['name'])
    except StopIteration:
        log.debug("No automation found")
        return None

    automation = []
    data = None
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


def parse(data):
    processed = []
    for spell in data:
        log.info(f"Parsing {spell['name']}...")
        parsetime(spell)
        parserange(spell)
        parsecomponents(spell)
        parseduration(spell)
        parseclasses(spell)

        ritual = spell.get('meta', {}).get('ritual', False)
        desc = render(spell['entries'])
        if 'entriesHigherLevel' in spell:
            higherlevels = render(spell['entriesHigherLevel']) \
                .replace("**At Higher Levels**: ", "")
        else:
            higherlevels = None

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
            "page": spell['page'],
            "concentration": spell['concentration'],
            "automation": get_automation(spell)
        }
        processed.append(recursive_tag(newspell))
    return processed


def dump(data, filename='spells.json'):
    with open(f'out/{filename}', 'w') as f:
        json.dump(data, f, indent=2)


def get_auto_only(data):
    return [{
        "name": spell['name'],
        "automation": spell['automation']
    } for spell in data]


def run():
    data = get_spells()
    processed = parse(data)
    dump(processed)
    dump(get_auto_only(processed), 'spellauto.json')


if __name__ == '__main__':
    run()
