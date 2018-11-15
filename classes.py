import logging

from lib.parsing import recursive_tag, render
from lib.utils import dump, get_indexed_data, remove_ignored

SRD = ('Barbarian', 'Bard', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock',
       'Wizard')
SRD_SUBCLASSES = ('College of Lore', 'Life Domain', 'Circle of the Land', 'Champion', 'Way of the Open Hand',
                  'Oath of Devotion', 'Hunter', 'Thief', 'Draconic Bloodline', 'The Fiend', 'School of Evocation')
IGNORED_SOURCES = ('Stream',)

log = logging.getLogger("classes")


def get_classes_from_web():
    return get_indexed_data('class/', 'classes.json', 'class')


def filter_ignored(data):
    for _class in data:
        _class['subclasses'] = remove_ignored(_class['subclasses'], IGNORED_SOURCES)
    return data


def srdfilter(data):
    for _class in data:
        if _class['name'] in SRD:
            _class['srd'] = True
        else:
            _class['srd'] = False

        for subclass in _class['subclasses']:
            if subclass['name'] in SRD_SUBCLASSES:
                subclass['srd'] = True
            else:
                subclass['srd'] = False
    return data


def parse_classfeats(data):
    out = []
    for _class in data:
        log.info(f"Parsing classfeats for class {_class['name']}...")
        for level in _class.get('classFeatures', []):
            for feature in level:
                fe = {
                    'name': f"{_class['name']}: {feature['name']}",
                    'text': render(feature['entries']), 'srd': _class['srd']
                }
                log.info(f"Found feature: {fe['name']}")
                out.append(fe)
                options = [e for e in feature['entries'] if
                           isinstance(e, dict) and e.get('type') == 'options']
                for option in options:
                    for opt_entry in option.get('entries', []):
                        fe = {
                            'name': f"{_class['name']}: {feature['name']}: {_resolve_name(opt_entry)}",
                            'text': f"{render(opt_entry['entries'])}",
                            'srd': _class['srd']

                        }
                        log.info(f"Found option: {fe['name']}")
                        out.append(fe)
                subentries = [e for e in feature['entries'] if
                              isinstance(e, dict) and e.get('type') == 'entries']
                for opt_entry in subentries:
                    fe = {
                        'name': f"{_class['name']}: {feature['name']}: {_resolve_name(opt_entry)}",
                        'text': f"{render(opt_entry['entries'])}",
                        'srd': _class['srd']

                    }
                    log.info(f"Found subentry: {fe['name']}")
                    out.append(fe)
        for subclass in _class.get('subclasses', []):
            log.info(f"Parsing classfeats for subclass {subclass['name']}...")
            for level in subclass.get('subclassFeatures', []):
                for feature in level:
                    options = [f for f in feature.get('entries', []) if
                               isinstance(f, dict) and f['type'] == 'options']  # battlemaster only
                    for option in options:
                        for opt_entry in option.get('entries', []):
                            fe = {
                                'name': f"{_class['name']}: {option['name']}: "
                                        f"{_resolve_name(opt_entry)}",
                                'text': render(opt_entry['entries']),
                                'srd': subclass.get('srd', False)
                            }
                            log.info(f"Found option: {fe['name']}")
                            out.append(fe)
                    for entry in feature.get('entries', []):
                        if not isinstance(entry, dict): continue
                        if not entry.get('type') == 'entries': continue
                        fe = {
                            'name': f"{_class['name']}: {subclass['name']}: {entry['name']}",
                            'text': render(entry['entries']), 'srd': subclass.get('srd', False)
                        }
                        log.info(f"Found feature: {fe['name']}")
                        out.append(fe)
                        options = [e for e in entry['entries'] if
                                   isinstance(e, dict) and e.get('type') == 'options']
                        for option in options:
                            for opt_entry in option.get('entries', []):
                                fe = {
                                    'name': f"{_class['name']}: {subclass['name']}: {entry['name']}: "
                                            f"{_resolve_name(opt_entry)}",
                                    'text': render(opt_entry['entries']),
                                    'srd': subclass.get('srd', False)
                                }
                                log.info(f"Found option: {fe['name']}")
                                out.append(fe)
                        subentries = [e for e in entry['entries'] if
                                      isinstance(e, dict) and e.get('type') == 'entries']
                        for opt_entry in subentries:
                            fe = {
                                'name': f"{_class['name']}: {subclass['name']}: {entry['name']}: "
                                        f"{_resolve_name(opt_entry)}",
                                'text': f"{render(opt_entry['entries'])}",
                                'srd': _class['srd']

                            }
                            log.info(f"Found subentry: {fe['name']}")
                            out.append(fe)
    return out


def _resolve_name(entry):
    """Resolves the next name of a data entry.
    :param entry (dict) - the entry.
    :returns str - The next found name, or None."""
    if 'entries' in entry and 'name' in entry['entries'][0] and isinstance(entry['entries'][0], dict):
        return _resolve_name(entry['entries'][0])
    elif 'name' in entry:
        return entry['name']
    else:
        log.warning(f"No name found for {entry}")


def run():
    data = get_classes_from_web()
    data = filter_ignored(data)
    data = srdfilter(data)
    data = recursive_tag(data)
    classfeats = parse_classfeats(data)
    dump(data, 'classes.json')
    dump(classfeats, 'classfeats.json')


if __name__ == '__main__':
    run()
