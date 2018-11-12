import copy
import json
import logging

from lib.utils import get_json, dump, fix_dupes, remove_ignored, explicit_sources

SRD = ('Dragonborn', 'Half-Elf', 'Half-Orc', 'Elf (High)', 'Dwarf (Hill)', 'Human', 'Human (Variant)',
       'Halfling (Lightfoot)', 'Gnome (Rock)', 'Tiefling')
SOURCE_HIERARCHY = ('MTF', 'VGM', 'PHB', 'DMG', 'GGR', 'UAWGtE', 'UA', 'nil')
IGNORED_SOURCES = ('UARacesOfRavnica', 'UACentaursMinotaurs', 'UAEladrinAndGith', 'UAFiendishOptions')
EXPLICIT_SOURCES = ('UAEberron', 'DMG')

log = logging.getLogger("races")


def get_races_from_web():
    try:
        with open('cache/races.json') as f:
            races = json.load(f)
            log.info("Loaded race data from cache")
    except FileNotFoundError:
        races = get_json('races.json')['race']
        with open('cache/races.json', 'w') as f:
            json.dump(races, f, indent=2)
    return races


def split_subraces(races):
    out = []
    for race in races:
        log.info(f"Processing race {race['name']}")
        if 'subraces' not in race:
            out.append(race)
        else:
            subraces = race['subraces']
            del race['subraces']
            for subrace in subraces:
                log.info(f"Processing subrace {subrace.get('name')}")
                new = copy.deepcopy(race)
                if 'name' in subrace:
                    new['name'] = f"{race['name']} ({subrace['name']})"
                if 'entries' in subrace:
                    new['entries'].extend(subrace['entries'])
                if 'ability' in subrace:
                    if 'ability' in new:
                        new['ability'].update(subrace['ability'])
                    else:
                        new['ability'] = subrace['ability']
                if 'speed' in subrace:
                    new['speed'] = subrace['speed']
                if 'source' in subrace:
                    new['source'] = subrace['source']
                out.append(new)
    return out


def srdfilter(data):
    for race in data:
        if race['name'] in SRD:
            race['srd'] = True
        else:
            race['srd'] = False
    return data


def run():
    data = get_races_from_web()
    data = split_subraces(data)
    data = explicit_sources(data, EXPLICIT_SOURCES)
    data = fix_dupes(data, SOURCE_HIERARCHY)
    data = remove_ignored(data, IGNORED_SOURCES)
    data = srdfilter(data)
    dump(data, 'races.json')


if __name__ == '__main__':
    run()
