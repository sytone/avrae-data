import logging

from lib.parsing import recursive_tag
from lib.utils import dump, get_indexed_data, remove_ignored

SRD = ('Barbarian', 'Bard', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock',
       'Wizard')
SRD_SUBCLASSES = ('College of Lore', 'Life Domain', 'Circle of the Land', 'Champion', 'Way of the Open Hand',
                  'Oath of Devotion', 'Hunter', 'Thief', 'Draconic Bloodline', 'The Fiend', 'School of Evocation')
IGNORED_SOURCES = ('Stream')

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


def run():
    data = get_classes_from_web()
    data = filter_ignored(data)
    data = srdfilter(data)
    data = recursive_tag(data)
    dump(data, 'classes.json')


if __name__ == '__main__':
    run()
