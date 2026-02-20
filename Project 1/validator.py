import json
import os
import re
from html.parser import HTMLParser
from typing import Dict, List


def load_tokens(path: str) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("tokens", {})


class SimpleHTMLChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.open_tags = []

    def handle_starttag(self, tag, attrs):
        self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if tag in self.open_tags:
            # remove last occurrence
            for i in range(len(self.open_tags) - 1, -1, -1):
                if self.open_tags[i] == tag:
                    del self.open_tags[i]
                    break


def validate_syntax(files: Dict[str, str]) -> List[str]:
    errors = []
    for name, content in files.items():
        if name.endswith(".ts") or name.endswith('.tsx'):
            # very simple bracket balance check
            if content.count('{') != content.count('}'):
                errors.append(f"Unbalanced braces in {name}")
            if content.count('(') != content.count(')'):
                errors.append(f"Unbalanced parentheses in {name}")
        if name.endswith('.html'):
            parser = SimpleHTMLChecker()
            try:
                parser.feed(content)
                if parser.open_tags:
                    errors.append(f"Unclosed HTML tags in {name}: {parser.open_tags[:5]}")
            except Exception as e:
                errors.append(f"HTML parse error in {name}: {e}")
        if name.endswith('.scss') or name.endswith('.css'):
            if content.count('{') != content.count('}'):
                errors.append(f"Unbalanced CSS braces in {name}")
    return errors


def validate_tokens_usage(files: Dict[str, str], tokens: Dict[str, str]) -> List[str]:
    errors = []
    flat = "\n".join(files.values()).lower()
    for key, val in tokens.items():
        v = val.lower()
        # allow checking hex and rgba or token name
        if v not in flat and key.lower() not in flat:
            errors.append(f"Token '{key}' with value '{val}' not found in generated output")
    return errors


def validate_all(files: Dict[str, str], tokens_path: str) -> List[str]:
    tokens = load_tokens(tokens_path)
    errs = []
    errs.extend(validate_tokens_usage(files, tokens))
    errs.extend(validate_syntax(files))
    return errs


if __name__ == "__main__":
    import sys
    from generator import parse_files_from_response

    if len(sys.argv) < 2:
        print("Usage: validator.py <file-with-generated-text>")
        sys.exit(1)
    txt = open(sys.argv[1], 'r', encoding='utf-8').read()
    files = parse_files_from_response(txt)
    errs = validate_all(files, os.path.join(os.path.dirname(__file__), 'design-tokens.json'))
    if errs:
        print("Errors found:")
        for e in errs:
            print('-', e)
    else:
        print("No errors detected")
