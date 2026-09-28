"""Snap-derived transforms and append-only, three-dimensional branch topology.

Only upright rotations are used: ports must face each other. Native collision
meshes and pier exclusion volumes are not available here; their validity is a
separate native gate, never inferred from a successful snap alignment check.
"""
import math


def rotate(v, yaw):
    a = math.radians(yaw)
    return (math.cos(a)*v[0] + math.sin(a)*v[2], v[1],
            -math.sin(a)*v[0] + math.cos(a)*v[2])


def add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def snaps(catalog, macro):
    result = {}
    for n in catalog.component(macro).findall('connections/connection'):
        if 'snap' not in n.get('tags', '').split():
            continue
        if n.get('parent'):
            raise ValueError(f'{macro}: parented snap needs explicit transform resolution')
        pos = n.find('offset/position')
        q = n.find('offset/quaternion')
        x, y, z, w = [float(q.get(k, '0')) for k in ('qx', 'qy', 'qz', 'qw')] if q is not None else (0, 0, 0, 1)
        norm = math.sqrt(x*x+y*y+z*z+w*w)
        x,y,z,w = (v/norm for v in (x,y,z,w))
        normal = (2*(x*z+w*y), 2*(y*z-w*x), 1-2*(x*x+y*y))
        up = (2*(x*y-w*z), 1-2*(x*x+z*z), 2*(y*z+w*x))
        result[n.get('name').lower()] = {'position': tuple(float(pos.get(k, '0')) for k in ('x','y','z')) if pos is not None else (0,0,0),
                                         'normal': normal, 'up': up, 'aligned': 'snap_aligned' in n.get('tags','').split(),
                                         'quaternion': (x,y,z,w)}
    if not result:
        raise ValueError(f'{macro}: no snap connections')
    return result


class Layout:
    def __init__(self, catalog, selection, lengths=(800,1200,1600), pier_first=False, snap_variant=0, vertical_count=3, pier_storage_drop=False):
        self.catalog, self.selection = catalog, selection
        self.lengths, self.pier_first = lengths, pier_first
        self.snap_variant = snap_variant
        self.vertical_count = vertical_count
        self.pier_storage_drop = pier_storage_drop
        self.entries, self.used = [], set()
        self.ports = {}

    def ports_for(self, macro):
        if macro not in self.ports:
            self.ports[macro] = snaps(self.catalog, macro)
        return self.ports[macro]

    def root(self):
        self.entries.append(dict(index=1, macro=self.selection['cross'], position=(0,0,0), yaw=0, level=1, role='connector'))
        return 1

    def port(self, index, direction):
        e = self.entries[index-1]
        choices = [name for name,p in self.ports_for(e['macro']).items()
                   if (index,name) not in self.used and distance(rotate(p['normal'],e['yaw']), direction) < 0.001]
        if not choices:
            raise ValueError(f'entry {index} {e["macro"]}: no free port facing {direction}')
        return min(choices)

    def attach(self, parent, direction, macro, level, role='connector'):
        previous = self.entries[parent-1]
        parentport = self.port(parent, direction)
        anchor = add(previous['position'], rotate(self.ports_for(previous['macro'])[parentport]['position'], previous['yaw']))
        parent_snap=self.ports_for(previous['macro'])[parentport]
        candidates = []
        for name,p in self.ports_for(macro).items():
            if abs(direction[1])<0.001 and abs(p['normal'][1])<0.001:
                yaws=[math.degrees(math.atan2(-direction[0],-direction[2])-math.atan2(p['normal'][0],p['normal'][2])) % 360]
            else:
                target_up=rotate(parent_snap['up'],previous['yaw'])
                yaws=[math.degrees(math.atan2(target_up[0],target_up[2])-math.atan2(p['up'][0],p['up'][2])) % 360,0,90,180,270]
            for yaw in yaws:
                if distance(rotate(p['normal'],yaw), tuple(-v for v in direction)) < 0.001:
                    if (p['aligned'] or parent_snap['aligned']) and distance(rotate(p['up'],yaw),rotate(parent_snap['up'],previous['yaw']))>0.001:
                        continue
                    position = sub(anchor,rotate(p['position'],yaw))
                    candidates.append((yaw,name,position))
        if not candidates:
            raise ValueError(f'{macro}: no upright snap facing {direction}')
        # Choose an outward origin, then the shortest offset and deterministic yaw.
        def rank(c):
            projection=sum(v*d for v,d in zip(sub(c[2],anchor),direction))
            return (projection < -0.01, abs(projection), c[0], c[1])
        ranked=sorted(set(candidates),key=rank)
        yaw, own, position = ranked[self.snap_variant % len(ranked) if role in ('dock','pier') else 0]
        index = len(self.entries)+1
        self.entries.append(dict(index=index,macro=macro,position=position,yaw=yaw,
                                 predecessor=parent,parent_connection=parentport,connection=own,level=level,role=role))
        self.used.update(((parent,parentport),(index,own)))
        return index

    def branch(self, parent, direction, macro, level, role, length):
        origin = self.entries[parent-1]['position']
        end = parent
        for _ in range(20):
            if distance(self.entries[end-1]['position'],origin) >= length:
                break
            end = self.attach(end,direction,self.selection['straight'],level)
        else:
            raise ValueError('Branch length did not converge')
        if role!='connector' and not any(abs(p['normal'][1])<0.001 for p in self.ports_for(macro).values()):
            end=self.attach(end,direction,self.selection['cross'],level)
            direction=(0,-1,0) if any(p['normal'][1]>0.999 for p in self.ports_for(macro).values()) else (0,1,0)
        return self.attach(end,direction,macro,level,role)

    def free_directions(self, index, horizontal=True):
        e=self.entries[index-1]
        return [rotate(p['normal'],e['yaw']) for name,p in sorted(self.ports_for(e['macro']).items())
                if (index,name) not in self.used and (not horizontal or abs(p['normal'][1])<0.001)]

    def generate(self):
        centre = self.root()
        # Three branches per deck also accommodates native Boron/Split Y junctions.
        # Each branch has an inner storage junction and outward dock/pier arms.
        decks = {0: centre}
        spine_top = centre
        plans=[]
        for level in range(1,11):
            tier = 0 if level<4 else 1 if level<7 else 2
            deck = (level-1)//3
            if deck not in decks:
                for _ in range(self.vertical_count):
                    spine_top=self.attach(spine_top,(0,1,0),self.selection['vertical'],level)
                spine_top=self.attach(spine_top,(0,1,0),self.selection['cross'],level)
                decks[deck]=spine_top
            direction=self.free_directions(decks[deck])[0]
            junction=self.branch(decks[deck],direction,self.selection['cross'],level,'connector',self.lengths[0])
            storage=self.selection['storage'][tier]
            vertical=[p for p in self.ports_for(storage).values() if p['normal'][1]>0.999]
            if vertical:
                storage_parent=junction
                # The measured Split middle pier envelope touches its level-6
                # storage. A local drop avoids adding unnecessary connectors
                # at the other pier levels or moving any previous entry.
                if self.pier_storage_drop and level == 6:
                    storage_parent=self.attach(junction,(0,-1,0),self.selection['vertical'],level)
                self.attach(storage_parent,(0,-1,0),storage,level,'storage')
            else:
                storage_direction=min(self.free_directions(junction),key=lambda v: sum(a*b for a,b in zip(v,direction)))
                self.attach(junction,storage_direction,storage,level,'storage')
            roles=[('dock',(1,4,7,10)),('pier',(1,6,10))]
            for role,milestones in (roles[::-1] if self.pier_first else roles):
                if level in milestones:
                    outward=max(self.free_directions(junction),key=lambda v: sum(a*b for a,b in zip(v,direction)))
                    self.branch(junction,outward,self.selection[role][tier],level,role,self.lengths[1 if role=='dock' else 2])
            # Entries contain scalars and immutable position tuples only.
            # Each level owns its dictionaries for the later centring pass.
            plans.append([e.copy() for e in self.entries])
        # Centre the FULL planned height once; all early levels share that origin.
        shift=tuple((max(e['position'][i] for e in self.entries)+min(e['position'][i] for e in self.entries))/2 for i in range(3))
        for plan in plans:
            for e in plan:
                e['position']=tuple(round(v,5) for v in sub(e['position'],shift))
        return plans


def validate(plans, catalog, selection):
    previous=[]
    for level, entries in enumerate(plans,1):
        if entries[:len(previous)] != previous:
            raise ValueError(f'level {level}: changed existing entry')
        used=set()
        for i,e in enumerate(entries,1):
            if e['index'] != i or max(abs(x) for x in e['position']) > 5000:
                raise ValueError(f'level {level}: index/origin outside 10 km plot: {e}')
            if i==1:
                if 'predecessor' in e: raise ValueError('root has predecessor')
                continue
            if not 1 <= e['predecessor'] < i: raise ValueError('disconnected/cyclic graph')
            parent=entries[e['predecessor']-1]
            a=snaps(catalog,parent['macro'])[e['parent_connection']]
            b=snaps(catalog,e['macro'])[e['connection']]
            if distance(add(parent['position'],rotate(a['position'],parent['yaw'])),add(e['position'],rotate(b['position'],e['yaw']))) > 0.01:
                raise ValueError('misaligned snap positions')
            if distance(rotate(a['normal'],parent['yaw']),tuple(-x for x in rotate(b['normal'],e['yaw']))) > 0.001:
                raise ValueError('misaligned snap normals')
            if (a['aligned'] or b['aligned']) and distance(rotate(a['up'],parent['yaw']),rotate(b['up'],e['yaw']))>0.001:
                raise ValueError('misaligned locked snap roll')
            for port in ((e['predecessor'],e['parent_connection']),(i,e['connection'])):
                if port in used: raise ValueError('reused snap port')
                used.add(port)
        for role, milestones in [('storage',range(1,11)),('dock',(1,4,7,10)),('pier',(1,6,10))]:
            expected=[selection[role][0 if n<4 else 1 if n<7 else 2] for n in milestones if n<=level]
            if [e['macro'] for e in entries if e['role']==role] != expected:
                raise ValueError(f'level {level}: invalid {role} basket')
        if level>=7 and len({round(e['position'][1]) for e in entries if e['role']!='connector'})<3:
            raise ValueError('fewer than three functional elevations')
        previous=entries
