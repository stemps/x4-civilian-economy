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
from check_timings import Timings

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "src"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, default=Path(os.environ.get("X4_REFERENCE", ROOT.parent.parent / "reference")))
    parser.add_argument("--toolkit", type=Path, default=Path(os.environ.get("X4_TOOLKIT", ROOT.parent.parent)))
    parser.add_argument("--schema", action="store_true")
    parser.add_argument("--skip-tests", action="store_true", help="Run static/schema checks without controller tests")
    parser.add_argument("--timings", action="store_true", help="Report stages, test modules and slowest tests")
    args = parser.parse_args()
    timings = Timings(args.timings)
    try:
        return run_checks(args, timings)
    finally:
        timings.report()


def run_checks(args, timings):
    reference = args.reference.resolve()
    # Tests load the exact deployed XML, not a separate runtime implementation.
    os.environ["CE_REFERENCE"] = str(reference)
    if args.skip_tests:
        print("Controller tests omitted (--skip-tests); static validation still runs.", flush=True)
    else:
        with timings.stage('test discovery'):
            suite = unittest.defaultTestLoader.discover(str(ROOT / "tests" / "mod"))
        with timings.stage('controller tests'):
            result = timings.runner().run(suite)
        if not result.wasSuccessful():
            return 1
    with timings.stage('XML parsing and UI schema'):
        for file in MOD.rglob("*.xml"):
            if not any(p.startswith(".") for p in file.relative_to(MOD).parts):
                etree.parse(str(file))
        etree.XMLSchema(etree.parse(str(reference / "ui/core/addon.xsd"))).assertValid(etree.parse(str(MOD / "ui.xml")))
    toolkit = args.toolkit.resolve()
    package = toolkit / "tools" / "x4validate"
    sys.path.insert(0, str(package))
    # The toolkit's Windows venv launcher may be inaccessible in a sandbox.
    # Append pure-Python dependencies without shadowing this interpreter's lxml.
    sys.path.append(str(package / ".venv" / "Lib" / "site-packages"))
    from x4validate._cli import main as validate
    sys.argv = ["x4validate", str(MOD), "--reference", str(reference)]
    if args.schema:
        sys.argv.append("--update")
    with timings.stage('toolkit validation (including native schemas)' if args.schema else 'toolkit validation'):
        result = validate()
    if args.schema and not result:
        with timings.stage('merged diff schemas'):
            return validate_merged(reference)
    return result or 0


def apply_patch(base, patch, path):
    for change in patch.getroot():
        if not isinstance(change.tag, str):
            continue
        matches = base.xpath(change.get('sel'))
        if len(matches) != 1:
            raise ValueError(f'Patch selector is not unique: {path}: {change.get("sel")}')
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
        elif change.tag == 'add' and change.get('pos') is None:
            target.extend(deepcopy(child) for child in change)
        else:
            raise ValueError(f'Unsupported patch operation: {path}: {change.tag}')


def validate_merged(reference):
    # x4validate reports diff-rooted AI and MD scripts as uncheckable. Validate
    # the merged native scripts ourselves, reporting only newly introduced errors.
    from x4validate import _xsd
    merged_failed = False
    for folder, root_tag, xsd in (('aiscripts', 'aiscript', 'aiscripts.xsd'), ('md', 'mdscript', 'md.xsd')):
        compiled = _xsd._compiled(str(reference / "libraries" / xsd))
        for path in sorted((MOD / folder).glob('*.xml')):
            patch = etree.parse(str(path))
            if patch.getroot().tag == root_tag:
                if folder == 'aiscripts':
                    compiled.assertValid(patch)
                continue
            if patch.getroot().tag != 'diff':
                raise ValueError(f'Expected a diff: {path}')
            base = etree.parse(str(reference / folder / path.name))
            compiled.validate(base)
            baseline = {e.message for e in compiled.error_log}
            apply_patch(base, patch, path)
            compiled.validate(base)
            introduced = {e.message for e in compiled.error_log} - baseline
            if introduced:
                print(f'Merged {folder}/{path.name} schema failures:', *sorted(introduced), sep='\n')
                merged_failed = True
            else:
                print(f'Merged {folder}/{path.name} schema: no introduced errors')
    if merged_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
