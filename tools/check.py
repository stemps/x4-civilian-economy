"""Local static checks plus the toolkit validator. No game/profile writes.

Run with a Python containing lxml (the Codex bundled Python works).
--schema includes the expensive Egosoft XSD compilation in x4validate.
"""
from pathlib import Path
import argparse
import sys
import unittest
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, default=ROOT.parent.parent / "reference")
    parser.add_argument("--toolkit", type=Path, default=ROOT.parent.parent)
    parser.add_argument("--schema", action="store_true")
    args = parser.parse_args()
    reference = args.reference.resolve()
    # Tests load the exact deployed XML, not a separate runtime implementation.
    import os
    os.environ["CE_REFERENCE"] = str(reference)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        return 1
    for file in ROOT.rglob("*.xml"):
        if not any(p.startswith(".") for p in file.relative_to(ROOT).parts):
            etree.parse(str(file))
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
        base = etree.parse(str(reference / "aiscripts" / "build.buildstorage.xml"))
        patch = etree.parse(str(ROOT / "aiscripts" / "build.buildstorage.xml"))
        compiled = _xsd._compiled(str(reference / "libraries" / "aiscripts.xsd"))
        compiled.validate(base)
        baseline = {e.message for e in compiled.error_log}
        for change in patch.getroot():
            if not isinstance(change.tag, str):
                continue
            matches = base.xpath(change.get("sel"))
            if change.tag != "replace" or len(matches) != 1:
                raise ValueError("Unexpected build-storage patch structure")
            matches[0].getparent().set(matches[0].attrname, change.text)
        compiled.validate(base)
        introduced = {e.message for e in compiled.error_log} - baseline
        if introduced:
            print("Merged AI schema failures:", *sorted(introduced), sep="\n")
            return 1
        print("Merged build-storage AI schema: no introduced errors")
    return result or 0


if __name__ == "__main__":
    raise SystemExit(main())
