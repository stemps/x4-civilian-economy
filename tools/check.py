"""Local static checks plus the toolkit validator. No game/profile writes.

Run with a Python containing lxml (the Codex bundled Python works).
--schema includes the expensive Egosoft XSD compilation in x4validate.
"""
from pathlib import Path
import argparse
import os
import sys
import unittest
from copy import deepcopy
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, default=Path(os.environ.get("X4_REFERENCE", ROOT.parent.parent / "reference")))
    parser.add_argument("--toolkit", type=Path, default=Path(os.environ.get("X4_TOOLKIT", ROOT.parent.parent)))
    parser.add_argument("--schema", action="store_true")
    args = parser.parse_args()
    reference = args.reference.resolve()
    # Tests load the exact deployed XML, not a separate runtime implementation.
    os.environ["CE_REFERENCE"] = str(reference)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        return 1
    for file in ROOT.rglob("*.xml"):
        if not any(p.startswith(".") for p in file.relative_to(ROOT).parts):
            etree.parse(str(file))
    etree.XMLSchema(etree.parse(str(reference / "ui/core/addon.xsd"))).assertValid(etree.parse(str(ROOT / "ui.xml")))
    toolkit = args.toolkit.resolve()
    package = toolkit / "tools" / "x4validate"
    sys.path.insert(0, str(package))
    # The toolkit's Windows venv launcher may be inaccessible in a sandbox.
    # Append pure-Python dependencies without shadowing this interpreter's lxml.
    sys.path.append(str(package / ".venv" / "Lib" / "site-packages"))
    from x4validate._cli import main as validate
    sys.argv = ["x4validate", str(ROOT), "--reference", str(reference)]
    if args.schema:
        sys.argv.append("--update")
    result = validate()
    if args.schema and not result:
        # x4validate reports diff-rooted AI scripts as uncheckable. Validate the
        # merged native script ourselves, reporting only newly introduced errors.
        from x4validate import _xsd
        compiled = _xsd._compiled(str(reference / "libraries" / "aiscripts.xsd"))
        merged_failed = False
        for path in sorted((ROOT / 'aiscripts').glob('*.xml')):
            patch = etree.parse(str(path))
            if patch.getroot().tag == 'aiscript':
                compiled.assertValid(patch)
                continue
            if patch.getroot().tag != 'diff':
                raise ValueError(f'Expected an AI diff: {path}')
            base = etree.parse(str(reference / 'aiscripts' / path.name))
            compiled.validate(base)
            baseline = {e.message for e in compiled.error_log}
            for change in patch.getroot():
                if not isinstance(change.tag, str):
                    continue
                matches = base.xpath(change.get('sel'))
                if len(matches) != 1:
                    raise ValueError(f'AI selector is not unique: {path}: {change.get("sel")}')
                target=matches[0]
                if change.tag == 'replace' and getattr(target, 'is_attribute', False):
                    target.getparent().set(target.attrname, change.text)
                elif change.tag == 'replace':
                    parent=target.getparent(); index=parent.index(target)
                    parent.remove(target)
                    for child in change:
                        parent.insert(index,deepcopy(child));index+=1
                elif change.tag == 'add' and change.get('pos') in ('before','after','prepend'):
                    parent=target if change.get('pos') == 'prepend' else target.getparent()
                    index=0 if change.get('pos') == 'prepend' else parent.index(target) + (change.get('pos') == 'after')
                    for child in change:
                        parent.insert(index,deepcopy(child));index+=1
                else:
                    raise ValueError(f'Unsupported AI patch operation: {path}: {change.tag}')
            compiled.validate(base)
            introduced = {e.message for e in compiled.error_log} - baseline
            if introduced:
                print(f'Merged {path.name} schema failures:', *sorted(introduced), sep='\n')
                merged_failed = True
            else:
                print(f'Merged {path.name} AI schema: no introduced errors')
        if merged_failed:
            return 1
    return result or 0


if __name__ == "__main__":
    raise SystemExit(main())
