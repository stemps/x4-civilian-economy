"""Generate/check production racial connector-spine plans and their provenance."""
import argparse
import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from lxml import etree as E
from spine_catalog import Catalog, RACES
from spine_geometry import Layout, validate
from spine_bounds import fit

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'src'
PREFIX = 'ce_hub_'


def xml_bytes(root):
    return E.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)


def generate(reference, bounds_path=None):
    catalog = Catalog(reference)
    measurements=json.loads(bounds_path.read_text(encoding='utf-8')) if bounds_path else None
    constraints=json.loads((ROOT/'tests/mod/fixtures/spine_layout_constraints.json').read_text(encoding='utf-8'))
    if measurements and measurements.get('version') != 2:
        raise ValueError('Reimport native bounds with corrected half-extent semantics before generation')
    manifest = {'version': 1, 'evidence': 'reference base+DLC; not installed effective tree',
                'geometry_checks': 'snap positions/normals, graph, module origins inside plot; collision meshes and pier approaches UNMEASURED',
                'plot_metres': [10000,10000,10000], 'races': {}}
    manifest['native_bounds']=measurements
    manifest['layout_constraints']=constraints
    if measurements:
        manifest['geometry_checks']='snap graph, immutable prefixes, measured native AABB containment and conservative functional AABB separation; connector collisions and docking approaches UNMEASURED'
    plans=[]
    data=E.Element('mdscript',name='CE_ConstructionData')
    cues=E.SubElement(data,'cues')
    library=E.SubElement(cues,'library',name='Load')
    actions=E.SubElement(library,'actions')
    E.SubElement(actions,'set_value',name='$LayoutMacros',exact='[]')
    E.SubElement(actions,'set_value',name='$LayoutGeometry',exact='[]')
    for race in RACES:
        try:
            selection=catalog.select(race)
            if measurements:
                stages,fitting=fit(catalog,selection,measurements['macros'],constraints['races'].get(race))
            else:
                stages=Layout(catalog,selection).generate()
                fitting={'status':'PROVISIONAL: native bounds calibration required; first native smoke failed'}
            validate(stages,catalog,selection)
            manifest['races'][race]={'selection':selection,'levels':stages,'static_valid':True,'fitting':fitting}
            branch=E.SubElement(actions,'do_if',value=f"$LayoutRace == '{race}'")
            for level, entries in enumerate(stages,1):
                plan=E.Element('plan',id=f'{PREFIX}{race}_{level:02}',name='{974201,1}',description='{974201,2}',fixed='1')
                for entry in entries:
                    n=E.SubElement(plan,'entry',index=str(entry['index']),macro=entry['macro'])
                    if 'predecessor' in entry:
                        n.set('connection',entry['connection'])
                        E.SubElement(n,'predecessor',index=str(entry['predecessor']),connection=entry['parent_connection'])
                    offset=E.SubElement(n,'offset')
                    E.SubElement(offset,'position',**{k:f'{v:.5f}' for k,v in zip(('x','y','z'),entry['position'])})
                    E.SubElement(offset,'rotation',yaw=str(entry['yaw']))
                # Cumulative stages live in the manifest, not separate runtime plans.
                E.SubElement(branch,'append_to_list',name='$LayoutMacros',exact='['+','.join("'"+e['macro']+"'" for e in entries)+']')
                E.SubElement(branch,'append_to_list',name='$LayoutGeometry',exact='['+','.join(
                    '['+','.join(f'{v:.5f}' for v in (*e['position'],e['yaw']))+']' for e in entries)+']')
            # Vanilla prefabs mark stage endpoints with bookmark="1". The
            # final unmarked tail is the last stage, as in ARG prefab plans.
            staged=deepcopy(plan)
            staged.set('id',f'{PREFIX}{race}')
            endpoints={len(stage) for stage in stages[:-1]}
            for entry in staged.findall('entry'):
                if int(entry.get('index')) in endpoints: entry.set('bookmark','1')
            plans.append(staged)
            print(f'{race}: 10 levels, {len(stages[-1])} entries; static snap/graph checks PASS; '+('measured bounds fit PASS; docking UNMEASURED' if measurements else 'origins only; bounds UNMEASURED'),flush=True)
        except ValueError as exc:
            manifest['races'][race]={'static_valid':False,'failure':str(exc)}
            print(f'{race}: BLOCKED: {exc}')
    manifest['sources']=dict(sorted(catalog.fingerprints.items()))
    # Hash sources with normalized newlines: a CRLF checkout (core.autocrlf) must
    # not make identical generator code report the committed artifacts as stale.
    manifest['generator_sha256']={p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in
                                 (Path(__file__),Path(__file__).with_name('spine_catalog.py'),Path(__file__).with_name('spine_geometry.py'),Path(__file__).with_name('spine_bounds.py'))}
    manifest['fingerprint']=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    actions.insert(0,E.Element('set_value',name='$LayoutFingerprint',exact="'"+manifest['fingerprint']+"'"))
    return plans,data,manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,default=Path(os.environ.get('X4_REFERENCE',ROOT.parent.parent/'reference')))
    parser.add_argument('--write',action='store_true',help='Explicitly regenerate production artifacts; default is read-only verification.')
    parser.add_argument('--bounds',type=Path,help='Measured native calibration JSON. Missing data never becomes estimated bounds.')
    args=parser.parse_args()
    bounds_path=args.bounds or ROOT/'tests/mod/fixtures/spine_native_bounds.json'
    if not bounds_path.exists():
        if args.bounds: parser.error('Explicit bounds file does not exist')
        bounds_path=None
    plans,data,manifest=generate(args.reference,bounds_path)
    if args.write and any(not r['static_valid'] for r in manifest['races'].values()):
        parser.error('Unresolved race: refusing to replace existing artifacts with incomplete coverage')
    target=MOD/'libraries/constructionplans.xml'
    root=E.Element('diff')
    block=E.SubElement(root,'add',sel='/plans')
    block.extend(plans)
    updated=xml_bytes(root)
    artifacts={target:updated, MOD/'md/ce_construction_data.xml':xml_bytes(data),
               ROOT/'tests/mod/fixtures/spine_manifest.json':(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()}
    stale=[]
    for path,content in artifacts.items():
        if args.write:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(content)
        elif not path.exists() or path.read_bytes().replace(b'\r\n',b'\n')!=content:
            stale.append(str(path.relative_to(ROOT)))
    if stale:
        print('STALE/MISSING:',', '.join(stale))
    blocked=[r for r,v in manifest['races'].items() if not v['static_valid']]
    print('Evidence: six-race construction and visual review passed for approved geometry; actual docking untested.')
    return int(bool(stale or blocked))


if __name__=='__main__':
    raise SystemExit(main())
