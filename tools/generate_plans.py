"""Generate cumulative CE plans. Only our plan definitions are written."""
from copy import deepcopy
from pathlib import Path
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]


def plans():
    entries = []

    def add(macro, x, z, parent=None, own='connectionsnap002', snap='connectionsnap001'):
        e = E.Element('entry', index=str(len(entries) + 1), macro=macro)
        if parent:
            e.set('connection', own)
            E.SubElement(e, 'predecessor', index=str(parent), connection=snap)
        offset = E.SubElement(e, 'offset')
        E.SubElement(offset, 'position', x=str(x), y='0', z=str(z))
        E.SubElement(offset, 'rotation', yaw='0')
        entries.append(e)
        return len(entries)

    add('dockarea_arg_m_station_01_lowtech_macro', 0, 0)
    add('struct_arg_base_01_macro', 0, 400, 1)
    end = add('storage_arg_s_container_01_macro', 0, 1000, 2)
    add('pier_arg_harbor_01_macro', -799.956, 0.04400635, 1,
        own='connectionsnap001', snap='connectionsnap004')
    z = 1000
    end_half = 400
    result = []
    for level in range(1, 11):
        if level > 1:
            cross_z = z + end_half + 200
            cross = add('struct_arg_cross_01_macro', 0, cross_z, end)
            z = cross_z + 600
            end = add('storage_arg_s_container_01_macro', 0, z, cross)
            end_half = 400
            if level in (4, 7, 10):
                z += 600
                end = add('dockarea_arg_m_station_01_lowtech_macro', 0, z, end)
                end_half = 200
            if level in (6, 10):
                add('pier_arg_harbor_01_macro', -800, cross_z, cross,
                    own='connectionsnap001', snap='connectionsnap003')
        p = E.Element('plan', id=f'ce_ownerless_hub_{level:02}',
                      name='{974201,1}', description='{974201,2}')
        p.extend(deepcopy(entries))
        result.append(p)
    return result


if __name__ == '__main__':
    root = E.Element('diff')
    add = E.SubElement(root, 'add', sel='/plans')
    add.extend(plans())
    E.ElementTree(root).write(str(ROOT / 'libraries/constructionplans.xml'),
                             encoding='utf-8', xml_declaration=True, pretty_print=True)
    print('Cumulative module counts:', [len(p) for p in plans()])
