"""Native numeric bounds import and deterministic envelope fitting.

No meshes/assets are copied. AABB separation is a conservative screen, not a
docking/approach test. Missing measurements must never become estimated bounds.
"""
import argparse
import hashlib
import itertools
import json
import math
import re
from pathlib import Path

from spine_geometry import Layout, add, rotate, validate

NUMBER = r'[-+0-9.eE]+'
ROW = re.compile(r'\[CE Spine\] CALIBRATION macro=(\w+) max=('+NUMBER+r'),('+NUMBER+r'),('+NUMBER+r') center=('+NUMBER+r'),('+NUMBER+r'),('+NUMBER+r')')


def import_log(path):
    raw = Path(path).read_bytes()
    lines = raw.decode('utf-8', errors='replace').splitlines()
    # Never combine observations from separate runs or layouts silently.
    groups = []
    active = None
    for line in lines:
        begin = re.search(r'CALIBRATION_BEGIN token=(\d+) race=(\w+) fingerprint=(\w+)', line)
        if begin:
            key = (begin[1], begin[3])
            if not groups or begin[2]=='argon' or groups[-1]['key'] != key:
                groups.append({'key':key, 'macros': {}, 'races': set(), 'missing': set()})
            group=groups[-1]
            if begin[2] in group['races']:
                raise ValueError('Duplicate race calibration in one run')
            active = begin[2]
        elif active:
            group = groups[-1]
            row = ROW.search(line)
            if row:
                values = [float(v) for v in row.groups()[1:]]
                half_extent, center = values[:3], values[3:]
                minimum = [c-h for c,h in zip(center,half_extent)]
                maximum = [c+h for c,h in zip(center,half_extent)]
                if not all(math.isfinite(v) for v in values) or any(h<0 for h in half_extent):
                    raise ValueError('Invalid native bounds: '+row[1])
                box = {'min':minimum, 'max':maximum, 'native_max':half_extent, 'center':center}
                if row[1] in group['macros'] and group['macros'][row[1]] != box:
                    raise ValueError('Conflicting measurements: '+row[1])
                group['macros'][row[1]] = box
            missing = re.search(r'CALIBRATION_MISSING macro=(\w+)', line)
            if missing:
                group['missing'].add(missing[1])
            end = re.search(r'CALIBRATION_END race=(\w+)', line)
            if end:
                if end[1] != active:
                    raise ValueError('Mismatched calibration end')
                group['races'].add(end[1])
                active = None
    if not groups:
        raise ValueError('No native calibration records. Run the updated smoke test first.')
    group = groups[-1]
    key = group['key']
    from spine_catalog import RACES
    if group['races'] != set(RACES) or group['missing']:
        raise ValueError(f'Incomplete latest calibration: races={sorted(group["races"])} missing={sorted(group["missing"])}')
    return {'version':2, 'evidence':'MEASURED native max/center; corners derived as center +/- max, reconciled with native station spans; mesh collisions and approach volumes unmeasured',
            'log_sha256':hashlib.sha256(raw).hexdigest(), 'layout_fingerprint':key[1],
            'run_token':key[0], 'races':sorted(group['races']), 'macros':dict(sorted(group['macros'].items()))}


def box(entry, bounds):
    b = bounds[entry['macro']]
    if len(b['min']) != 3 or len(b['max']) != 3 or any(not math.isfinite(v) for v in b['min']+b['max']) or any(a>b for a,b in zip(b['min'],b['max'])):
        raise ValueError('Malformed bounds: '+entry['macro'])
    points = [add(entry['position'], rotate(p,entry['yaw'])) for p in itertools.product(*zip(b['min'], b['max']))]
    return tuple(min(p[i] for p in points) for i in range(3)), tuple(max(p[i] for p in points) for i in range(3))


def fit(catalog, selection, bounds, constraint=None):
    required = {selection[k] for k in ('cross','straight','vertical')}
    required.update(m for k in ('storage','dock','pier') for m in selection[k])
    missing = required - bounds.keys()
    if missing:
        raise ValueError('Missing native measurements: '+', '.join(sorted(missing)))
    best=None
    # Fixed finite search, reproducible on every machine. Extend this search if
    # measured constraints prove a race unresolved; never shrink its modules.
    candidates = [constraint['candidate']] if constraint else itertools.product((400,800,1200),(400,800,1200),(400,800,1200,1600),(False,True),range(4),(3,4,5,6),(False,True))
    for inner,dock,pier,pier_first,snap_variant,vertical_count,storage_drop in candidates:
        try:
            stages=Layout(catalog,selection,(inner,dock,pier),pier_first,snap_variant,vertical_count,storage_drop).generate()
        except ValueError:
            continue  # This port/arm candidate cannot form the required graph.
        boxes=[box(e,bounds) for e in stages[-1]]
        lo=tuple(min(b[0][i] for b in boxes) for i in range(3))
        hi=tuple(max(b[1][i] for b in boxes) for i in range(3))
        if any(b-a>9900 for a,b in zip(lo,hi)):
            continue
        # Functional module AABBs must be separated. Connected connectors may
        # touch; this does not certify connector mesh clearance or approaches.
        functional=[b for e,b in zip(stages[-1],boxes) if e['role']!='connector']
        if any(all(a[0][i]<b[1][i]+50 and b[0][i]<a[1][i]+50 for i in range(3)) for a,b in itertools.combinations(functional,2)):
            continue
        score=(len(stages[-1]),inner,dock,pier,pier_first,snap_variant,vertical_count,storage_drop)
        if best is not None and score>=best[0]:
            continue
        shift=constraint['shift'] if constraint else tuple((a+b)/2 for a,b in zip(lo,hi))
        if any(a-s < -4950 or b-s > 4950 for a,b,s in zip(lo,hi,shift)):
            continue
        for stage in stages:
            for entry in stage:
                entry['position']=tuple(round(v-s,5) for v,s in zip(entry['position'],shift))
        try:
            validate(stages,catalog,selection)
        except ValueError:
            continue
        if constraint and hashlib.sha256(json.dumps(stages,sort_keys=True).encode()).hexdigest()!=constraint['levels_sha256']:
            raise ValueError('Preserved racial geometry changed')
        best=(score, stages,
                           {'branch_lengths':[inner,dock,pier], 'pier_first':pier_first,
                            'dock_pier_snap_variant':snap_variant,
                            'vertical_connectors_per_deck':vertical_count,
                            'extra_storage_drop_levels':[6] if storage_drop else [],
                            'envelope_size':[round(b-a,5) for a,b in zip(lo,hi)],
                            'plot_margin_metres':50,'functional_aabb_gap_metres':50,
                            'clearance_evidence':'conservative functional AABB screen only; docking and connector collisions UNMEASURED'})
    if best is None:
        raise ValueError('No candidate fits measured bounds and conservative functional separation in the 10 km plot')
    _,stages,report=best
    return stages,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    result=import_log(args.log)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'Imported {len(result["macros"])} native macro bounds from six races; no docking acceptance implied')


if __name__=='__main__': main()
