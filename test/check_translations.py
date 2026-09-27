"""Translation coverage gate, mirrored from Supply Chain View's check_sources.

CE keeps English in 0001-l044.xml. All reference-game locales are required,
including the three not enabled in the current game's language registry.
Uses only the Python standard library; never contacts translation services.
"""

from collections import Counter
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "0001-l044.xml"
LANGUAGES = {7, 33, 34, 39, 42, 44, 48, 49, 55, 81, 82, 86, 88, 90, 359, 380}
# Lua arguments are positional by order; MD arguments are explicitly numbered.
TOKENS = re.compile(r"(?P<lua>%(?:%|[-+#0]*\d*(?:\.\d+)?[cdiouxXeEfgGqs]))|(?P<md>%[1-9]\d*)")
REFERENCES = re.compile(r"\{\d+,\d+\}")


def format_signature(text):
    matches = list(TOKENS.finditer(text))
    return (
        [match.group() for match in matches if match.lastgroup == "lua"],
        Counter(match.group() for match in matches if match.lastgroup == "md"),
        Counter(REFERENCES.findall(text)),
        text.count(r"\n"),
    )


def translation_coverage_errors(directory, languages=LANGUAGES):
    """Report every missing/extra/empty/duplicate entry across all pages/locales.

    Equal English text is allowed: shared terms, units and format-only entries
    are legitimate. This checks structure and formatting, not linguistic quality.
    """
    directory = Path(directory)
    errors = []

    def read(path):
        values = {}
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as exc:
            errors.append(f"{path.name}: {exc}")
            return values
        if root.tag != "language":
            errors.append(f"{path.name}: expected a language document")
        expected_id = str(int(path.stem.split("-l")[1]))
        if root.get("id") != expected_id:
            errors.append(f"{path.name}: language id must be {expected_id}")
        for page in root.findall("page"):
            for entry in page.findall("t"):
                key = (page.get("id"), entry.get("id"))
                label = f"{path.name}: page {key[0]}, text {key[1]}"
                if None in key:
                    errors.append(f"{label}: missing id attribute")
                if key in values:
                    errors.append(f"{label}: duplicate entry")
                values[key] = "".join(entry.itertext())
                if not values[key].strip():
                    errors.append(f"{label}: empty translation")
                if re.search(r"(?<!\\)[()]", values[key]):
                    errors.append(f"{label}: unescaped parentheses; X4 would strip visible text")
                if "\u2014" in values[key]:
                    errors.append(f"{label}: unsupported em dash; use a normal hyphen")
        if not values:
            errors.append(f"{path.name}: no text entries")
        return values

    source = read(directory / SOURCE)
    expected = {f"0001-l{language:03d}.xml" for language in languages} | {SOURCE}
    actual = {path.name for path in directory.glob("0001-l*.xml")}
    for name in sorted(expected - actual):
        errors.append(f"{name}: missing language file")
    for name in sorted(actual - {SOURCE}):
        if not re.fullmatch(r"0001-l\d{3}\.xml", name):
            errors.append(f"{name}: invalid language filename")
            continue
        values = read(directory / name)
        for page, entry in sorted(source.keys() - values.keys(), key=str):
            errors.append(f"{name}: page {page}, text {entry}: missing translation")
        for page, entry in sorted(values.keys() - source.keys(), key=str):
            errors.append(f"{name}: page {page}, text {entry}: absent from English source")
        for key in sorted(source.keys() & values.keys(), key=str):
            if format_signature(values[key]) != format_signature(source[key]):
                errors.append(f"{name}: page {key[0]}, text {key[1]}: formatting placeholders, references or line breaks differ")
    return errors


def main():
    errors = translation_coverage_errors(ROOT / "t")
    for error in errors:
        print(f"FAIL translations: {error}")
    if errors:
        return 1
    count = len(ET.parse(ROOT / "t" / SOURCE).findall("page/t"))
    print(f"PASS translations: {count} entries in each of {len(LANGUAGES)} required languages; formatting preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
