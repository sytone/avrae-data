import logging

from lib.parsing import render, recursive_tag
from lib.utils import get_data, dump

log = logging.getLogger("items")

ITEM_TYPES = {"G": "Adventuring Gear", "SCF": "Spellcasting Focus", "AT": "Artisan Tool", "T": "Tool",
              "GS": "Gaming Set", "INS": "Instrument", "A": "Ammunition", "M": "Melee Weapon", "R": "Ranged Weapon",
              "LA": "Light Armor", "MA": "Medium Armor", "HA": "Heavy Armor", "S": "Shield", "W": "Wondrous Item",
              "P": "Potion", "ST": "Staff", "RD": "Rod", "RG": "Ring", "WD": "Wand", "SC": "Scroll", "EXP": "Explosive",
              "GUN": "Firearm", "SIMW": "Simple Weapon", "MARW": "Martial Weapon", "$": "Valuable Object",
              'TAH': "Tack and Harness", 'TG': "Trade Goods", 'MNT': "Mount", 'VEH': "Vehicle", 'SHP': "Ship",
              'GV': "Generic Variant", 'AF': "Futuristic", 'siege weapon': "Siege Weapon", 'generic': "Generic"}

DMGTYPES = {"B": "bludgeoning", "P": "piercing", "S": "slashing", "N": "necrotic", "R": "radiant"}

SIZES = {"T": "Tiny", "S": "Small", "M": "Medium", "L": "Large", "H": "Huge", "G": "Gargantuan"}

PROPS = {"A": "ammunition", "LD": "loading", "L": "light", "F": "finesse", "T": "thrown", "H": "heavy", "R": "reach",
         "2H": "two-handed", "V": "versatile", "S": "special", "RLD": "reload", "BF": "burst fire", "CREW": "Crew",
         "PASS": "Passengers", "CARGO": "Cargo", "DMGT": "Damage Threshold", "SHPREP": "Ship Repairs"}


def get_latest_items():
    return get_data("items.json")['item'] + get_data("basicitems.json")['basicitem'] + get_data("magicvariants.json")[
        'variant']


def moneyfilter(data):
    return [i for i in data if not i.get('type') == "$"]


def variant_inheritance(data):
    for item in data:
        if item.get('type') == 'GV':
            if 'entries' in item:
                oldentries = item['entries'].copy()
                item.update(item['inherits'])
                item['entries'] = oldentries
            else:
                item.update(item['inherits'])
            del item['inherits']  # avrae doesn't parse it anyway
    return data


def get_objects():
    return get_data("objects.json")['object']


def object_actions(objects):
    for object in objects:
        if 'actionEntries' in object:
            object['entries'].append('__Actions__')
            object['entries'].append(render(object['actionEntries']))
            del object['actionEntries']  # also unparsed
    return objects


def srdfilter(data):
    with open('srd/srd-items.txt') as f:
        srd = [s.strip().lower() for s in f.read().split('\n')]

    for item in data:
        if item['name'].lower() in srd or (item.get('source') == 'PHB' and not item.get('wondrous')):
            item['srd'] = True
        else:
            item['srd'] = False
    return data


def prerender(data):
    for item in data:
        if 'entries' in item:
            item['desc'] = render(item['entries'])
            del item['entries']
        else:
            item['desc'] = ""

        for k, v in item.items():
            item[k] = recursive_tag(v)
    return data


def site_render(data):
    out = []
    for item in data:
        if not item['srd']:
            continue

        damage = ''
        extras = ''
        properties = []

        if 'type' in item:
            type_ = ', '.join(
                i for i in ([ITEM_TYPES.get(t, 'n/a') for t in item['type'].split(',')] +
                            ["Wondrous Item" if item.get('wondrous') else ''])
                if i)
            for iType in item['type'].split(','):
                if iType in ('M', 'R', 'GUN'):
                    damage = f"{item.get('dmg1', 'n/a')} {DMGTYPES.get(item.get('dmgType'), 'n/a')}" \
                        if 'dmg1' in item and 'dmgType' in item else ''
                    type_ += f', {item.get("weaponCategory")}'
                if iType == 'S': damage = f"AC +{item.get('ac', 'n/a')}"
                if iType == 'LA': damage = f"AC {item.get('ac', 'n/a')} + DEX"
                if iType == 'MA': damage = f"AC {item.get('ac', 'n/a')} + DEX (Max 2)"
                if iType == 'HA': damage = f"AC {item.get('ac', 'n/a')}"
                if iType == 'SHP':  # ships
                    extras = f"Speed: {item.get('speed')}\nCarrying Capacity: {item.get('carryingcapacity')}\n" \
                             f"Crew {item.get('crew')}, AC {item.get('vehAc')}, HP {item.get('vehHp')}"
                    if 'vehDmgThresh' in item:
                        extras += f", Damage Threshold {item['vehDmgThresh']}"
                if iType == 'siege weapon':
                    extras = f"Size: {SIZES.get(item.get('size'), 'Unknown')}\n" \
                             f"AC {item.get('ac')}, HP {item.get('hp')}\n" \
                             f"Immunities: {item.get('immune')}"
        else:
            type_ = ', '.join(
                i for i in ("Wondrous Item" if item.get('wondrous') else '', item.get('technology')) if i)
        rarity = str(item.get('rarity')).replace('None', '')
        if 'tier' in item:
            if rarity:
                rarity += f', {item["tier"]}'
            else:
                rarity = item['tier']
        type_and_rarity = type_ + (f", {rarity}" if rarity else '')
        value = (item.get('value', 'n/a') + (', ' if 'weight' in item else '')) if 'value' in item else ''
        weight = (item.get('weight', 'n/a') + (' lb.' if item.get('weight') == '1' else ' lbs.')) \
            if 'weight' in item else ''
        weight_and_value = value + weight
        for prop in item.get('property', []):
            if not prop: continue
            a = b = prop
            a = PROPS.get(a, 'n/a')
            if b == 'V': a += " (" + item.get('dmg2', 'n/a') + ")"
            if b in ('T', 'A'): a += " (" + item.get('range', 'n/a') + "ft.)"
            if b == 'RLD': a += " (" + item.get('reload', 'n/a') + " shots)"
            properties.append(a)
        properties = ', '.join(properties)
        damage_and_properties = f"{damage} - {properties}" if properties else damage
        damage_and_properties = (' --- ' + damage_and_properties) if weight_and_value and damage_and_properties else \
            damage_and_properties

        meta = f"*{type_and_rarity}*\n{weight_and_value}{damage_and_properties}\n{extras}"
        text = item['desc']

        out.append({'name': item['name'], 'meta': meta, 'desc': text})
    return out


def run():
    data = get_latest_items()
    data = moneyfilter(data)
    data = variant_inheritance(data)
    objects = get_objects()
    objects = object_actions(objects)
    data.extend(objects)
    data = srdfilter(data)
    data = prerender(data)
    sitedata = site_render(data)
    dump(data, 'items.json')
    dump(sitedata, 'template-items.json')


if __name__ == '__main__':
    run()
