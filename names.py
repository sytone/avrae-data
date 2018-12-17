import logging

from lib.utils import get_data, dump

log = logging.getLogger("names")


def get_names():
    return get_data("names.json")['name']


def clean_tables(names):
    for race in names:
        log.info(f"Parsing names for {race['race']}")
        tables = []
        for table in race['tables']:
            log.info(f"Parsing option {table['option']}")
            new_table = {'name': table['option'], 'choices': []}
            for choice in table['table']:
                new_table['choices'].append(choice['enc'])
            tables.append(new_table)
        race['tables'] = tables

    return names


def run():
    data = get_names()
    data = clean_tables(data)
    dump(data, 'names.json')


if __name__ == '__main__':
    run()
