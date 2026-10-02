"""Deterministic envelope fitting against measured native module bounds.

No meshes/assets are copied. AABB separation is a conservative screen, not a
docking/approach test. Missing measurements must never become estimated bounds.
"""
import hashlib
import itertools
import json
import math

from spine_geometry import Layout, add, rotate, validate


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

