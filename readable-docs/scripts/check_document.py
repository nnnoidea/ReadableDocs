#!/usr/bin/env python3
"""Check source resources and HTML conversion fidelity; not semantic or visual quality."""
import argparse
import base64
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote_to_bytes, urlsplit

from export_html import FORMAT, local_path, pandoc_path, run
from workspace import resources


def normalized(text):
    return re.sub(r'\s+', ' ', text).strip()


class Content(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.text = []
        self.images = []
        self.links = []
        self.codes = []
        self.tables = []
        self.ids = set()
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        skip = (bool(self.stack and self.stack[-1][1]) or tag in ('head', 'style', 'script')
                or attrs.get('id') in ('TOC', 'title-block-header') or 'toc-panel' in attrs.get('class', '').split())
        if tag not in self.VOID:self.stack.append((tag, skip))
        if skip:return
        if 'id' in attrs:self.ids.add(attrs['id'])
        if tag == 'img':self.images.append((attrs.get('src', ''), attrs.get('alt', '')))
        if tag == 'a':self.links.append(attrs.get('href', ''))
        if tag == 'pre':self.codes.append([])
        if tag == 'table':self.tables.append([])
        if tag in ('td', 'th') and self.tables:self.tables[-1].append([])

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.stack and self.stack[-1][1]:return
        self.text.append(data)
        tags = [v[0] for v in self.stack]
        if 'pre' in tags:self.codes[-1].append(data)
        if ('td' in tags or 'th' in tags) and self.tables and self.tables[-1]:self.tables[-1][-1].append(data)


def image_bytes(target, directory):
    if target.startswith('data:image/'):
        metadata, payload = target.split(',', 1)
        return base64.b64decode(payload) if ';base64' in metadata else unquote_to_bytes(payload)
    path = local_path(target, directory)
    if path is None:raise ValueError(f'Image is not local or embedded: {target}')
    return path.read_bytes()


def link_key(target, directory):
    path = local_path(target, directory)
    url = urlsplit(target)
    return (str(path), url.query, url.fragment) if path else target


def check(source, html=None):
    source = Path(source).resolve()
    markdown = source.read_text(encoding='utf-8')
    files = resources(markdown, source.parent)
    result = {'scope': 'Mechanical integrity only; semantic and visual review remain with the Agent.',
              'source': str(source), 'local_resources': len(files)}
    if html is None:return result
    html = Path(html).resolve()
    expected = Content(run(pandoc_path(), ['--from', FORMAT, '--to', 'html5', '--mathml', '--fail-if-warnings'], markdown))
    actual = Content(html.read_text(encoding='utf-8'))
    errors = []
    if normalized(''.join(expected.text)) != normalized(''.join(actual.text)):errors.append('Body text differs')
    codes = lambda doc: [''.join(v).rstrip('\n') for v in doc.codes]
    if codes(expected) != codes(actual):errors.append('Code blocks differ')
    tables = lambda doc: [[normalized(''.join(cell)) for cell in table] for table in doc.tables]
    if tables(expected) != tables(actual):errors.append('Table cells or order differ')
    if [link_key(v, source.parent) for v in expected.links] != [link_key(v, html.parent) for v in actual.links]:
        errors.append('Links or their order differ')
    if len(expected.images) != len(actual.images):errors.append('Image count differs')
    else:
        for i, ((a, alt_a), (b, alt_b)) in enumerate(zip(expected.images, actual.images), 1):
            if alt_a != alt_b or image_bytes(a, source.parent) != image_bytes(b, html.parent):errors.append(f'Image {i} differs')
            if not b.startswith('data:image/'):errors.append(f'Image {i} is not embedded')
    for link in actual.links:
        if link.startswith('#') and link[1:] not in actual.ids:errors.append(f'Missing anchor: {link}')
    result.update(html=str(html), images=len(actual.images), tables=len(actual.tables), code_blocks=len(actual.codes), errors=errors)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('html', type=Path, nargs='?')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:result = check(args.source, args.html)
    except (ValueError, OSError) as error:parser.error(str(error))
    report = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding='utf-8')
    print(report, end='')
    if result.get('errors'):raise SystemExit(1)
