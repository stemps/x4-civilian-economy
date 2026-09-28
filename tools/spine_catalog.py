"""Read-only base/DLC module catalogue for the isolated spine experiment.

This is reference evidence, not an effective installed-mod merge. Fingerprints
include every XML file actually read. No game assets are copied into the mod.
"""
from pathlib import Path
import hashlib
from lxml import etree as E

RACES = {'argon': 'arg', 'boron': 'bor', 'paranid': 'par',
         'split': 'spl', 'terran': 'ter', 'teladi': 'tel'}


class Catalog:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.files = {}
        self.fingerprints = {}
        self.cache = {}
        for base in [self.root / 'assets', *sorted(self.root.glob('extensions/*/assets'))]:
            for path in base.rglob('*.xml'):
                self.files.setdefault(path.stem.lower(), []).append(path)
        self.groups = {}
        for path in [self.root / 'libraries/modulegroups.xml',
                     *sorted(self.root.glob('extensions/*/libraries/modulegroups.xml'))]:
            for group in self.read(path).xpath('//group[@name]'):
                self.groups.setdefault(group.get('name'), set()).update(
                    n.get('macro') for n in group.findall('select') if n.get('macro'))

    def read(self, path):
        data = path.read_bytes()
        self.fingerprints[path.relative_to(self.root).as_posix()] = hashlib.sha256(data).hexdigest()
        return E.fromstring(data)

    def node(self, name, kind='macro'):
        key = (name.lower(), kind)
        if key not in self.cache:
            paths = self.files.get(name.lower(), [])
            if len(paths) != 1:
                raise ValueError(f'{name}: expected one reference definition, found {len(paths)}')
            nodes = self.read(paths[0]).xpath(f'./{kind}[@name="{name}"]')
            if len(nodes) != 1:
                raise ValueError(f'{name}: missing {kind} definition')
            self.cache[key] = nodes[0]
        return self.cache[key]

    def component(self, macro):
        return self.node(self.node(macro).find('component').get('ref'), 'component')

    def capacity(self, name):
        node = self.node(name)
        cargo = node.find('properties/cargo')
        storage = int(cargo.get('max', '0')) if cargo is not None and 'container' in cargo.get('tags', '').split() else 0
        docks = {'dock_s': 0, 'dock_m': 0, 'capital': 0}
        for child in node.findall('connections/connection/macro'):
            if not child.get('ref'):
                continue  # Empty component placeholder, not an attached bay.
            bay = self.node(child.get('ref'))
            if bay.get('class') != 'dockingbay':
                continue
            size = bay.find('properties/docksize')
            tags = size.get('tags', '').split() if size is not None else []
            for tag in ('dock_s', 'dock_m'):
                docks[tag] += tag in tags
            docks['capital'] += bool({'dock_l', 'dock_xl'} & set(tags))
        return {'storage': storage, 'dock': docks['dock_s'] + docks['dock_m']
                if docks['dock_s'] and docks['dock_m'] else 0,
                'pier': docks['capital'], **docks}

    def select(self, race):
        code = RACES[race]
        families = {'storage': [f'stor_{code}'],
                    'dock': [g for g in self.groups if g == f'dockarea_{code}' or g.startswith(f'dockarea_{code}_')],
                    'pier': [f'pier_base_{code}', f'pier_add_{code}']}
        result = {}
        for role, groups in families.items():
            choices = sorted(set().union(*(self.groups.get(g, set()) for g in groups)))
            scored = [(self.capacity(n)[role], n) for n in choices if self.capacity(n)[role] > 0]
            capacities = sorted({s for s, _ in scored})
            if not capacities:
                raise ValueError(f'{race}: no {role} candidates')
            tiers = [capacities[0], capacities[len(capacities)//2], capacities[-1]]
            result[role] = [min(n for s, n in scored if s == score) for score in tiers]
            result[role + '_candidates'] = [{'macro': n, 'capacity': s} for s, n in sorted(scored)]
        connectors = sorted(self.groups.get(f'conn_{code}', []))
        # Exact connector families are explicitly scoped to this prototype.
        for role, suffix in [('cross', 'cross_01'), ('straight', 'base_01'), ('vertical', 'vertical_01')]:
            macro = f'struct_{code}_{suffix}_macro'
            if macro not in connectors:
                raise ValueError(f'{race}: missing prototype connector {macro}')
            result[role] = macro
        return result
