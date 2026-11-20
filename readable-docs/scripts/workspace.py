#!/usr/bin/env python3
"""Mechanical chapter, snapshot and handoff operations. Never decides review outcomes."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import quote

from export_html import FORMAT, local_path, pandoc_path, run


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def headings(text):
    offset = 0
    fence = None
    frontmatter = text.startswith('---\n') or text.startswith('---\r\n')
    for n, line in enumerate(text.splitlines(keepends=True)):
        if frontmatter:
            if n and line.strip() in ('---', '...'):frontmatter = False
        elif fence:
            if re.match(r'^ {0,3}' + re.escape(fence[0]) + '{' + str(fence[1]) + r',}\s*$', line):fence = None
        else:
            match = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
            if match:fence = (match[1][0], len(match[1]))
            else:
                match = re.match(r'^ {0,3}(#{1,6})[ \t]+(.+?)\s*#*\s*$', line)
                if match:yield offset, offset + len(line), len(match[1]), match[2]
        offset += len(line)


def split(draft):
    draft = Path(draft).resolve()
    text = draft.read_text(encoding='utf-8')
    root = draft.parent
    markers = [h for h in headings(text) if h[3] == '文档草稿']
    if len(markers) > 1:raise ValueError('Use one 文档草稿 heading to separate the brief and publication body')
    brief, body = (text[:markers[0][0]], text[markers[0][1]:]) if markers else ('', text)
    cuts = [h for h in headings(body) if h[2] == 2]
    if not cuts:cuts = [(0, 0, 2, next((h[3] for h in headings(body)), '正文'))]
    files = {'intro.md': body[:cuts[0][0]]}
    if brief.strip():files['brief.md'] = brief
    chapters = []
    # A substantive introduction receives its own reviewable chapter.
    if re.sub(r'^# .*(?:\n|$)', '', files['intro.md'], flags=re.M).strip():
        files['00.md'] = files['intro.md']
        files['intro.md'] = ''
        chapters.append({'id': '00', 'title': '开篇', 'file': '00.md'})
    for i, h in enumerate(cuts):
        ident = f'{i+1:02}'
        filename = ident + '.md'
        files[filename] = body[h[0]:cuts[i+1][0] if i+1 < len(cuts) else len(body)]
        chapters.append({'id': ident, 'title': h[3], 'file': filename})
    files['chapters.json'] = json.dumps({'intro': 'intro.md', 'chapters': chapters}, ensure_ascii=False, indent=2) + '\n'
    if any((root / name).exists() for name in files):
        raise ValueError('Chapter files already exist; edit them directly or use a fresh source directory')
    for name, content in files.items():(root / name).write_text(content, encoding='utf-8')
    return {'source': str(root), 'chapters': len(chapters), 'manifest': str(root / 'chapters.json')}


def manifest(source):
    source = Path(source).resolve()
    data = json.loads((source / 'chapters.json').read_text(encoding='utf-8'))
    for name in [data['intro'], *(v['file'] for v in data['chapters'])]:
        path = (source / name).resolve()
        if source not in path.parents or not path.is_file():raise ValueError(f'Invalid chapter path: {name}')
    ids = [v['id'] for v in data['chapters']]
    if not ids or len(ids) != len(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in ids):
        raise ValueError('Chapter IDs must be unique simple names')
    return source, data


def assemble(source):
    source, data = manifest(source)
    parts = [(source / data['intro']).read_text(encoding='utf-8')]
    parts.extend((source / v['file']).read_text(encoding='utf-8') for v in data['chapters'])
    body = ''
    for part in parts:
        if body and part and not body.endswith('\n'):body += '\n'
        body += part
    output = source / 'document.md'
    if output.name in [data['intro'], *(v['file'] for v in data['chapters'])]:
        raise ValueError('document.md is reserved for the assembled publication')
    output.write_text(body, encoding='utf-8')
    return output


def new_directory(destination, build):
    destination = Path(destination).resolve()
    if destination.exists():raise ValueError(f'Snapshot already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.rd-') as tmp:
        staging = Path(tmp) / 'snapshot'
        staging.mkdir()
        build(staging)
        staging.rename(destination)
    return destination


def snapshot(source, destination):
    source, _ = manifest(source)
    destination = Path(destination).resolve()
    if destination == source or source in destination.parents:raise ValueError('Save stage snapshots outside source/')
    assemble(source)
    def build(staging):
        shutil.copytree(source, staging, dirs_exist_ok=True)
        hashes = {str(p.relative_to(staging)): digest(p) for p in staging.rglob('*') if p.is_file()}
        (staging / 'snapshot.json').write_text(json.dumps(hashes, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'snapshot': str(new_directory(destination, build))}


def resources(markdown, source):
    ast = json.loads(run(pandoc_path(), ['--from', FORMAT, '--to', 'json', '--fail-if-warnings'], markdown))
    found = set()
    def visit(node):
        if isinstance(node, dict):
            if node.get('t') in ('Image', 'Link'):
                target = node['c'][-1][0]
                path = local_path(target, source)
                if node['t'] == 'Image' and path is None and not target.startswith('data:image/'):
                    raise ValueError(f'Save the image in source/ first: {target}')
                if path is not None:
                    if not path.is_file():raise ValueError(f'Missing resource: {path}')
                    if source not in path.parents:raise ValueError(f'Keep local resources inside source/: {path}')
                    found.add(path)
                    if node['t'] == 'Image':
                        for suffix in ('.json', '.py', '.svg', '.png'):
                            sidecar = path.with_suffix(suffix)
                            if sidecar.is_file():found.add(sidecar)
            for value in node.values():visit(value)
        elif isinstance(node, list):
            for value in node:visit(value)
    visit(ast)
    return found


def pair(source, ident, destination, stage):
    source, data = manifest(source)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', stage):raise ValueError('Use a simple snapshot stage name')
    chapter = next((v for v in data['chapters'] if v['id'] == ident), None)
    if chapter is None:raise ValueError(f'Unknown chapter: {ident}')
    pair_root = Path(destination).resolve() / ident
    if pair_root == source or source in pair_root.parents:raise ValueError('Save pairs outside source/')
    if stage != 'before' and not (pair_root / 'before').is_dir():raise ValueError('Save before before editing this chapter')
    if stage not in ('before', 'after') and not (pair_root / 'after').is_dir():raise ValueError('Save the initial after before review revisions')
    text = (source / chapter['file']).read_text(encoding='utf-8')
    files = resources(text, source) | {source / chapter['file']}
    if (source / 'brief.md').exists():files.add(source / 'brief.md')
    # Shared data/styles are explicit authoring resources; no generated semantic judgments.
    for name in ('data', 'colors.json', 'document.css'):
        path = source / name
        if path.is_dir():files.update(p for p in path.rglob('*') if p.is_file())
        elif path.is_file():files.add(path)
    def build(staging):
        hashes = {}
        for path in sorted(files):
            relative = path.relative_to(source)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            hashes[str(relative)] = digest(target)
        (staging / 'snapshot.json').write_text(json.dumps({'chapter': chapter, 'files': hashes}, ensure_ascii=False, indent=2), encoding='utf-8')
    output = new_directory(pair_root / stage, build)
    result = {'snapshot': str(output), 'chapter': ident, 'resources': len(files)-1}
    if stage != 'before':
        baseline = pair_root / ('before' if stage == 'after' else 'after')
        report = pair_root / (stage + '.diff')
        report.write_text(compare(baseline, output), encoding='utf-8')
        result['diff'] = str(report)
    return result


def compare(before, after):
    before, after = Path(before), Path(after)
    if not before.is_dir() or not after.is_dir():raise ValueError('Both comparison directories must exist')
    paths = sorted({p.relative_to(root) for root in (before, after) for p in root.rglob('*') if p.is_file() and p.name != 'snapshot.json'})
    result = []
    for relative in paths:
        a, b = before / relative, after / relative
        if a.is_file() and b.is_file() and digest(a) == digest(b):continue
        if relative.suffix.lower() in ('.md', '.json', '.py', '.css', '.svg', '.txt', '.csv'):
            left = a.read_text(encoding='utf-8').splitlines(keepends=True) if a.exists() else []
            right = b.read_text(encoding='utf-8').splitlines(keepends=True) if b.exists() else []
            result.extend(difflib.unified_diff(left, right, fromfile='before/'+str(relative), tofile='after/'+str(relative)))
        else:result.append(f'Resource changed: {relative}\n')
    return ''.join(result) or 'No file changes.\n'


def index(source, destination, review=None):
    source, data = manifest(source)
    destination = Path(destination).resolve()
    def link(path):
        import os
        return quote(Path(os.path.relpath(path, destination.parent)).as_posix(), safe='/')
    lines = ['# 交付索引', '']
    for name, label in [('document.md','正文'),('document.html','HTML 阅读版'),('brief.md','写作依据')]:
        if (source / name).exists():lines.append(f'- [{label}]({link(source/name)})')
    if review:
        path = Path(review).resolve()
        if not path.is_file():raise ValueError(f'Missing review record: {path}')
        lines.append(f'- [检查记录]({link(path)})')
    lines += ['', '| 章节 | 文件 | 已记录的来源 |', '| --- | --- | --- |']
    for row in data['chapters']:
        title = row['title'].replace('|', '\\|')
        sources = '; '.join(row.get('sources', [])).replace('|', '\\|') or '—'
        lines.append(f"| {title} | [{row['id']}]({link(source/row['file'])}) | {sources} |")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return {'index': str(destination)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('split');p.add_argument('draft', type=Path)
    p = sub.add_parser('assemble');p.add_argument('source', type=Path)
    p = sub.add_parser('snapshot');p.add_argument('source', type=Path);p.add_argument('destination', type=Path)
    p = sub.add_parser('pair');p.add_argument('source', type=Path);p.add_argument('chapter');p.add_argument('destination', type=Path);p.add_argument('--stage', required=True)
    p = sub.add_parser('diff');p.add_argument('before', type=Path);p.add_argument('after', type=Path);p.add_argument('--output', type=Path)
    p = sub.add_parser('index');p.add_argument('source', type=Path);p.add_argument('destination', type=Path);p.add_argument('--review', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'split':result = split(args.draft)
        elif args.command == 'assemble':result = {'document': str(assemble(args.source))}
        elif args.command == 'snapshot':result = snapshot(args.source, args.destination)
        elif args.command == 'pair':result = pair(args.source, args.chapter, args.destination, args.stage)
        elif args.command == 'index':result = index(args.source, args.destination, args.review)
        else:
            result = compare(args.before, args.after)
            if args.output:args.output.parent.mkdir(parents=True, exist_ok=True);args.output.write_text(result, encoding='utf-8');result = {'diff': str(args.output)}
    except (OSError, ValueError, KeyError) as error:parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else result)
