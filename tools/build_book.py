"""Build a local reader without changing authored prose or source manifests."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = '.'
START = '<!-- BOOK-CONTENT-START -->'
END = '<!-- BOOK-CONTENT-END -->'


def read(path):
    return path.read_bytes().decode('utf-8-sig')


def write(path, text):
    path.write_bytes(text.encode('utf-8'))


def esc(value):
    return html.escape(str(value), quote=True)


def digest(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def original_body(document):
    """Retain exact source text between content markers on subsequent builds."""
    if START in document:
        content = document.split(START, 1)[1].split(END, 1)[0]
        match = re.search(r'name="book-content-sha256" content="([a-f0-9]+)"', document)
        if match and match[1] != digest(content):
            raise ValueError('Authored content changed after wrapping; inspect and remove old digest to authorize rebuilding.')
        return content
    match = re.search(r'<body\b[^>]*>([\s\S]*?)</body>', document, re.I)
    return match[1] if match else document


def plain(text):
    return html.unescape(re.sub('<[^>]+>', '', text)).strip()


def page(title, content, course, chapter=False, previous=None, following=None, math=True, lab=False):
    course_label = course['course']
    nav = [('index.html', 'Lectures'), ('source-map.html', 'Source map'),
           ('references.html', 'References'), ('numerical-lab.html', 'Numerical lab')]
    links = ''.join(f'<a href="{url}">{label}</a>' for url, label in nav)
    footer_nav = ''
    if chapter:
        back = f'<a rel="prev" href="{esc(previous.name)}">Previous available chapter</a>' if previous else '<span>First available chapter</span>'
        ahead = f'<a rel="next" href="{esc(following.name)}">Next available chapter</a>' if following else ('<span>End of book</span>' if course.get('_complete') else '<span>End of selected recordings</span>' if course.get('_all_chapters_available') else '<span>Further chapters pending</span>')
        footer_nav = f'<nav class="page-turn" aria-label="Chapter navigation">{back}<a href="index.html">Lecture index</a>{ahead}</nav>'
    toc = '<aside class="toc" id="chapter-toc" aria-label="On this page"><h2>On this page</h2></aside>' if chapter else ''
    guarded = f'{START}{content}{END}' if chapter or lab else content
    checksum = f'<meta name="book-content-sha256" content="{digest(content)}">' if chapter or lab else ''
    lab_assets = ''
    if lab:
        repo = ROOT
        if (repo / 'assets/lab.css').exists():
            lab_assets += '<link rel="stylesheet" href="assets/lab.css">'
        if (repo / 'assets/lab.js').exists():
            lab_assets += '<script defer src="assets/lab.js"></script>'
    math_scripts = '''<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']],processEscapes:true},svg:{fontCache:'local'},options:{skipHtmlTags:['script','noscript','style','textarea','pre','code']}};</script>
<script defer src="assets/mathjax-tex-svg.js"></script>''' if math else ''
    footer = ('Complete local reading edition; source and validation boundaries '
              'are recorded in this repository.' if course.get('_complete') else
              'Local edition in progress; a rendered page does not establish editorial completion.')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark light">{checksum}<title>{esc(title)} · {esc(course_label)}</title>
<link rel="stylesheet" href="assets/book.css">{math_scripts}<script defer src="assets/book.js"></script>{lab_assets}</head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><a class="brand" href="index.html">{esc(course_label)} · {esc(course['term'])}</a><nav class="course-nav" aria-label="Book">{links}</nav></header>
<div class="layout{'' if chapter else ' no-toc'}">{toc}<main id="main">
<div class="reading-tools" aria-label="Reading controls"><button id="theme-toggle" aria-pressed="false">Light theme</button><button id="text-toggle" aria-pressed="false">Larger text</button><button id="solutions-toggle" aria-pressed="false">Expand solutions</button><button id="print-page">Print with solutions</button></div>
<article id="chapter-content">{guarded}</article>{footer_nav}</main></div>
<footer class="site-footer">Independent textbook rewrite. The NPTEL IIT Bombay lecture playlist supplies the chronological spine; original exposition and primary-source extensions are separately attributed. {footer}</footer></body></html>'''


def chapter_metadata(path):
    sidecar = path.with_suffix('.meta.json')
    return json.loads(read(sidecar)) if sidecar.exists() else {}


def safe_url(url):
    return isinstance(url, str) and url.startswith(('https://', 'http://'))


def install_assets(repo):
    assets = repo / 'assets'
    assets.mkdir(exist_ok=True)
    for name in ('book.css', 'book.js', 'mathjax-tex-svg.js', 'mathjax-LICENSE'):
        if not (assets / name).exists():
            raise FileNotFoundError(f'Missing local reader asset: {name}')


def build(course):
    repo = ROOT
    if not repo.is_dir():
        return None
    manifest = repo / 'source-manifest.json'
    if manifest.exists():
        course = json.loads(read(manifest))
    install_assets(repo)
    # Authors create prose fragments before their source sidecars are stable.
    # Do not wrap a live fragment and impose its preservation guard mid-edit.
    chapters = sorted(p for p in repo.glob('chapter-[0-9][0-9]-*.html')
                      if p.with_suffix('.meta.json').exists())
    completion_path = repo / 'completion.json'
    completion = json.loads(read(completion_path)) if completion_path.exists() else {}
    complete = (completion.get('status') == 'complete' and
                len(chapters) == len(course['chapters']) and
                completion.get('chapter_count') == len(chapters))
    course['_complete'] = complete
    course['_all_chapters_available'] = len(chapters) == len(course['chapters'])
    for i, path in enumerate(chapters):
        content = original_body(read(path))
        title = re.search(r'<h1\b[^>]*>([\s\S]*?)</h1>', content, re.I)
        document = page(plain(title[1]) if title else path.stem, content, course, True,
                        chapters[i-1] if i else None,
                        chapters[i+1] if i+1 < len(chapters) else None)
        if original_body(document) != content:
            raise AssertionError('Content preservation failed')
        write(path, document)
    rows = []
    sections = []
    references = {}
    reviewed_count = 0
    for entry in course['chapters']:
        order = int(entry['order'])
        matches = [p for p in chapters if p.name.startswith(f'chapter-{order:02d}-')]
        if len(matches) > 1:
            raise ValueError(f'Multiple files for chapter {order}')
        chapter = matches[0] if matches else None
        title = esc(entry['title'])
        headline = f'<a href="{esc(chapter.name)}">{title}</a>' if chapter else title
        reviewed = bool(chapter and entry.get('chapter_status') == 'reviewed and locally validated')
        reviewed_count += reviewed
        status = ('Complete chapter' if complete and chapter else 'Reviewed · locally validated' if reviewed
                  else 'Draft available · review pending' if chapter else 'Chapter pending')
        status_class = 'complete' if (complete and chapter) or reviewed else 'pending'
        recordings = ' · '.join(f'<a href="{esc(r["url"])}">Lecture {r["lecture_number"]}</a>'
                                for r in course['lectures'] if r.get('chapter_order') == order)
        rows.append(f'<li data-lecture><h2>{order:02d}. {headline}</h2><span class="status {status_class}">{status}</span><p class="lecture-meta">Recordings: {recordings}</p></li>')
        metadata = chapter_metadata(chapter) if chapter else {}
        for section in metadata.get('sections', []):
            sections.append(dict(section, chapter=chapter.name))
        for source in metadata.get('references', []):
            if safe_url(source.get('url')):
                references[(source['url'], source.get('supports', ''))] = source
    overview_path = repo / 'book-overview.html'
    overview = read(overview_path) if overview_path.exists() else '<h2>Learning route and prerequisites</h2><p class="pending">A course-specific prerequisite map and cross-chapter learning route are pending editorial development.</p>'
    edition_note = ('All selected chapters have passed the recorded course completion gates.'
                    if complete else
                    'This reading edition is in progress. Available chapters remain drafts until their source, mathematical, numerical, and editorial checks have been recorded.')
    if not complete and reviewed_count:
        edition_note = (f'This reading edition is in progress. {reviewed_count} available chapter(s) have passed '
                        'independent editorial review and local validation. Course completion checks remain pending.')
    page_label = 'chapter pages' if complete or reviewed_count else 'draft chapter pages available'
    index = f'''<h1>{esc(course['course'])}: an independent textbook rewrite</h1><p>{esc(course['provider'])} · {esc(course['instructor'])} · {esc(course['term'])} · {len(course['chapters'])} chapters from {len(course['lectures'])} recordings · {len(chapters)} {page_label}.</p>
<p>{edition_note}</p>
{overview}
<div class="search-tools"><label class="search-label" for="lecture-search">Search chapters</label><input id="lecture-search" type="search" placeholder="Search chapter title, topic, or status"><p id="search-status" role="status" aria-live="polite">{len(course['chapters'])} chapters shown</p></div><ol class="lecture-list">{''.join(rows)}</ol>'''
    write(repo / 'index.html', page('Lecture index', index, course))
    existing_map = repo / 'source-map.json'
    if existing_map.exists():
        supplied = json.loads(read(existing_map))
        if isinstance(supplied, list):
            sections = supplied
        elif isinstance(supplied, dict) and not supplied.get('generated_from_chapter_sidecars') and isinstance(supplied.get('sections'), list):
            sections = supplied['sections']
    if not existing_map.exists() or (isinstance(supplied, dict) and supplied.get('generated_from_chapter_sidecars')):
        write(existing_map, json.dumps({'generated_from_chapter_sidecars': True,
                                      'status': ('reviewed section provenance' if (complete or reviewed_count == len(chapters)) and sections else 'provenance pending' if not sections else 'supplied metadata; review pending'),
                                      'sections': sections}, indent=2) + '\n')
    source_rows = []
    for row in sections:
        start, end = row.get('start'), row.get('end')
        video_id = row.get('video_id')
        recording = next((entry for entry in course['lectures'] if entry['id'] == video_id), None)
        recording_label = (f'Lecture {recording["lecture_number"]} · {video_id}' if recording
                           else f'Unverified recording: {video_id}' if video_id
                           else 'Original teaching; no recording' if start is None and end is None
                           else 'Recording association pending')
        duration = row.get('duration', recording.get('duration') if recording else None)
        span = (f'{start}–{end} s' if start is not None and end is not None
                else 'Original teaching; no recording span'
                if 'start' in row and 'end' in row and start is None and end is None
                else 'Recording span incomplete; review pending')
        fields = [row.get('chapter', ''), row.get('section', row.get('title', '')),
                  recording_label, span, f'{duration} s' if duration is not None else 'No recording duration',
                  row.get('lecture_material', ''), row.get('research_extension', ''),
                  row.get('teaching_construction', ''), row.get('evidence_class', '')]
        cells = [f'<td>{esc(value)}</td>' for value in fields]
        if recording:
            target = recording['url'] + (f'&t={int(start)}s' if isinstance(start, (int, float)) and start >= 0 else '')
            cells[2] = f'<td><a href="{esc(target)}">{esc(recording_label)}</a></td>'
        source_rows.append('<tr>' + ''.join(cells) + '</tr>')
    map_body = '<h1>Source map</h1><p>Transcript spans locate lecture material. They do not measure the proportion of original exposition.</p>'
    map_body += '<p><a href="source-validation-summary.json">Source acquisition and transcript provenance summary</a> records the separate source checks and their limitations.</p>'
    for orientation in course.get('orientation_recordings', []):
        map_body += (f'<h2>Course orientation</h2><p><a href="{esc(orientation["url"])}">'
                     f'{esc(orientation["title"])}</a> · {esc(orientation["duration"])} seconds. '
                     'This separate introductory recording is included in the source collection; '
                     'it is outside the 60 numbered lectures and 20 topic chapters.</p>')
    if source_rows:
        headers = ['Chapter', 'Section', 'Recording', 'Transcript span', 'Recording duration', 'Lecture material', 'Research extension', 'Teaching construction', 'Evidence class']
        map_body += '<table><thead><tr>' + ''.join(f'<th scope="col">{h}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join(source_rows) + '</tbody></table>'
    else:
        map_body += '<p class="pending">Section-level evidence maps are pending. No chapter-level source claims have been inferred from recording titles.</p>'
    write(repo / 'source-map.html', page('Source map', map_body, course))
    refs_body = '<h1>Primary references</h1>'
    if references:
        refs_body += '<ul>' + ''.join(f'<li><a href="{esc(s["url"])}">{esc(s.get("title", s["url"]))}</a><p>{esc(s.get("supports", "Claim-level description pending."))}</p></li>' for s in references.values()) + '</ul>'
    else:
        refs_body += '<p class="pending">Verified chapter references and the claims they support are pending. Consult source links inside any available draft chapter.</p>'
    write(repo / 'references.html', page('Primary references', refs_body, course))
    lab = repo / 'numerical-lab.html'
    if not lab.exists():
        body = '<h1>Numerical laboratory</h1><p class="pending">Interactive course experiments are pending.</p>'
        if (repo / 'numerical_lab.py').exists():
            body += '<p><a href="numerical_lab.py">Local Python numerical checks</a> are available as supporting code. Their existence alone does not establish a passing run.</p>'
        write(lab, page('Numerical laboratory', body, course, lab=True))
    else:
        write(lab, page('Numerical laboratory', original_body(read(lab)), course, lab=True))
    return {'course': course['course'], 'slug': course['slug'], 'drafts': len(chapters), 'recordings': len(course['lectures'])}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(build({'slug': SLUG}), indent=2))


if __name__ == '__main__':
    main()
