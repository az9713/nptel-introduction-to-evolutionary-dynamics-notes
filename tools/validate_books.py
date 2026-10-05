"""Check reader artifacts; mechanical passes never certify textbook completion."""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from build_book import ROOT, SLUG, original_body, read


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.h2_count = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'h2':
            self.h2_count += 1
        for key in ('href', 'src'):
            if key in attrs:
                self.links.append((tag, attrs[key]))


def seconds(value):
    if str(value).isdigit():
        return int(value)
    parts = re.fullmatch(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', str(value))
    if parts and any(parts.groups()):
        return sum(int(v or 0) * multiplier for v, multiplier in zip(parts.groups(), [3600, 60, 1]))
    return None


def static_checks(repo):
    files = sorted(p for p in repo.glob('*.html')
                   if not p.name.startswith('chapter-')
                   or p.with_suffix('.meta.json').exists())
    failures = []
    warnings = []
    documents = {p: Document(read(p)) for p in files}
    manifest = json.loads(read(repo / 'source-manifest.json'))
    durations = {item['id']: item.get('duration') for item in manifest['lectures']}
    source_map = repo / 'source-map.json'
    if source_map.exists():
        supplied = json.loads(read(source_map))
        sections = supplied if isinstance(supplied, list) else supplied.get('sections', [])
        for row in sections:
            start, end, video_id = row.get('start'), row.get('end'), row.get('video_id')
            label = f'{row.get("chapter", "source-map")}: {row.get("section", "section")}'
            if start is None and end is None:
                continue
            if video_id not in durations:
                failures.append(f'{label}: recording ID missing or absent from numbered-lecture manifest')
                continue
            duration = durations[video_id]
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not isinstance(duration, (int, float)) or not 0 <= start <= end <= duration:
                failures.append(f'{label}: section span is outside recording bounds or incomplete')
            if row.get('duration') is not None and row['duration'] != duration:
                failures.append(f'{label}: sidecar duration differs from recording manifest')
    links_checked = 0
    timestamps_checked = 0
    math_pages = 0
    for path, document in documents.items():
        text = read(path)
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text):
            failures.append(f'{path.name}: unexpected control characters; inspect text/TeX serialization')
        if re.search(r'\ufffd|â€|âˆ|â‰|Ã[\u0080-\u00bf]', text):
            failures.append(f'{path.name}: possible UTF-8 decoding damage; inspect visible text')
        duplicates = [key for key, count in collections.Counter(document.ids).items() if count > 1]
        if duplicates:
            failures.append(f'{path.name}: duplicate IDs: {duplicates}')
        if re.search(r'(?:[A-Za-z]:[\\/](?:Users|home)|file:///|/Users/|/home/)', text, re.I):
            failures.append(f'{path.name}: private local path found')
        if path.name.startswith('chapter-') or path.name == 'numerical-lab.html':
            try:
                body = original_body(text)
            except ValueError:
                failures.append(f'{path.name}: authored-content digest mismatch')
                body = ''
            stripped = re.sub(r'<(pre|code|script|style)\b[^>]*>[\s\S]*?</\1>', '', body, flags=re.I)
            delimiters = re.findall(r'(?<!\\)\$\$|(?<!\\)\$', stripped)
            if delimiters:
                math_pages += 1
                active = None
                for delimiter in delimiters:
                    if active is None:
                        active = delimiter
                    elif delimiter == active:
                        active = None
                    else:
                        failures.append(f'{path.name}: nested/mismatched dollar math delimiter')
                        break
                if active:
                    failures.append(f'{path.name}: unclosed dollar math delimiter')
            for opening, closing in [(r'\(', r'\)'), (r'\[', r'\]')]:
                if stripped.count(opening) != stripped.count(closing):
                    failures.append(f'{path.name}: unbalanced {opening} math delimiters')
            if not re.search(r'<h1\b', body, re.I):
                failures.append(f'{path.name}: missing chapter h1')
        for tag, target in document.links:
            url = urlsplit(target)
            if url.scheme in ('mailto', 'tel', 'data'):
                continue
            if url.scheme or url.netloc:
                if tag in ('script', 'link', 'img') and url.scheme in ('https', 'http'):
                    warnings.append(f'{path.name}: remote rendering asset {target}')
                if url.hostname in ('www.youtube.com', 'youtube.com', 'youtu.be'):
                    query = parse_qs(url.query)
                    video = query.get('v', [url.path.lstrip('/') if url.hostname == 'youtu.be' else ''])[0]
                    value = query.get('t', query.get('start', [None]))[0]
                    if value is not None:
                        timing = seconds(value)
                        duration = durations.get(video)
                        if timing is None or duration is None:
                            warnings.append(f'{path.name}: timestamp lacks supported format or manifest duration')
                        elif timing < 0 or timing > duration:
                            failures.append(f'{path.name}: timestamp exceeds recording bounds')
                        else:
                            timestamps_checked += 1
                continue
            links_checked += 1
            destination = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not destination.is_relative_to(repo.resolve()):
                failures.append(f'{path.name}: link escapes standalone repository')
                continue
            if not destination.exists():
                failures.append(f'{path.name}: missing local target {url.path}')
                continue
            if url.fragment and destination.suffix == '.html':
                linked = documents.get(destination) or Document(read(destination))
                fragment = unquote(url.fragment)
                generated = re.fullmatch(r'section-(\d+)', fragment)
                if fragment not in linked.ids and not (generated and int(generated[1]) <= linked.h2_count):
                    failures.append(f'{path.name}: missing fragment {url.fragment} in {destination.name}')
    for name in ('book.css', 'book.js', 'mathjax-tex-svg.js', 'mathjax-LICENSE'):
        if not (repo / 'assets' / name).is_file():
            failures.append(f'missing asset {name}')
    if not files:
        failures.append('No rendered HTML pages exist')
    return {'status': 'failed' if failures else 'passed', 'html_files': len(files),
            'local_links_checked': links_checked, 'timestamps_checked': timestamps_checked,
            'chapter_pages_with_dollar_math': math_pages, 'failures': failures,
            'warnings': sorted(set(warnings))}


def browser_checks(repo, executable_path=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {'status': 'not performed', 'reason': 'Python Playwright is not installed'}
    findings = []
    failures = []
    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(**({'executable_path': str(executable_path)} if executable_path else {}))
            except Exception as exc:
                if executable_path or "Executable doesn't exist" not in str(exc):
                    raise
                browser = playwright.chromium.launch(channel='chrome')
            for path in sorted(p for p in repo.glob('*.html')
                               if not p.name.startswith('chapter-')
                               or p.with_suffix('.meta.json').exists()):
                if path.name == 'book-overview.html':
                    continue  # Authoring fragment embedded and tested in index.html.
                for width in (1280, 390):
                    context = browser.new_context(viewport={'width': width, 'height': 900})
                    context.route('http://**', lambda route: route.abort())
                    context.route('https://**', lambda route: route.abort())
                    page = context.new_page()
                    page.goto(path.as_uri(), wait_until='load')
                    page.wait_for_function('Boolean(window.MathJax && MathJax.startup && MathJax.startup.promise)')
                    page.evaluate('async () => { await MathJax.startup.promise; }')
                    result = page.evaluate('''() => ({mathErrors: document.querySelectorAll('mjx-merror,[data-mjx-error]').length,
                      mathNodes: document.querySelectorAll('mjx-container').length,
                      horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 2,
                      controls: ['theme-toggle','text-toggle','print-page'].every(id => !!document.getElementById(id)),
                      emptyToc: !!document.getElementById('chapter-toc') && !document.querySelector('#chapter-toc a')})''')
                    result.update(file=path.name, viewport=width)
                    source_body = original_body(read(path)) if path.name.startswith('chapter-') else ''
                    if re.search(r'\\[\[(]|(?<!\\)\$', source_body) and not result['mathNodes']:
                        failures.append(f'{path.name}: source mathematics produced no MathJax nodes')
                    findings.append(result)
                    if result['mathErrors'] or result['horizontalOverflow'] or not result['controls'] or result['emptyToc']:
                        failures.append(f'{path.name}: DOM/layout failure at width {width}')
                    page.emulate_media(media='print')
                    page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
                    if page.locator('details:not([open])').count():
                        failures.append(f'{path.name}: solutions remain closed for print')
                    page.evaluate("window.dispatchEvent(new Event('afterprint'))")
                    page.emulate_media(media='screen')
                    if path.name.startswith('chapter-'):
                        preview = 'preview.png' if width == 1280 else 'preview-mobile.png'
                        page.screenshot(path=str(repo / 'assets' / preview), full_page=False)
                    if width == 1280:
                        old_theme = page.evaluate("document.body.classList.contains('light')")
                        page.locator('#theme-toggle').click()
                        if page.evaluate("document.body.classList.contains('light')") == old_theme:
                            failures.append(f'{path.name}: theme control failed')
                        page.locator('#theme-toggle').click()
                        old_size = page.locator('#chapter-content').evaluate('(el) => getComputedStyle(el).fontSize')
                        page.locator('#text-toggle').click()
                        if page.locator('#chapter-content').evaluate('(el) => getComputedStyle(el).fontSize') == old_size:
                            failures.append(f'{path.name}: text-size control failed')
                        page.locator('#text-toggle').click()
                        if page.locator('article details').count():
                            page.locator('#solutions-toggle').click()
                            if page.locator('article details:not([open])').count():
                                failures.append(f'{path.name}: solution expansion failed')
                            page.locator('#solutions-toggle').click()
                        if page.locator('pre code').count():
                            # A chapter may intentionally collapse its long source listing.
                            # Open outer disclosures first, as a reader must before copying.
                            ancestors = page.locator('pre code').first.locator('xpath=ancestor::details').all()
                            for disclosure in reversed(ancestors):
                                if not disclosure.evaluate('(el) => el.open'):
                                    disclosure.locator(':scope > summary').click()
                            expected = page.locator('pre code').first.text_content()
                            page.evaluate('''() => {
                              window.__copiedCode = null;
                              Object.defineProperty(navigator, 'clipboard', {configurable:true,value:{writeText:async()=>{throw new Error('test fallback')}}});
                              document.execCommand = (cmd) => {window.__copiedCode = document.activeElement.value;return cmd === 'copy';};
                            }''')
                            code = page.locator('pre code').first
                            copy_button = code.locator('xpath=..').locator('.copy-code:visible')
                            if not copy_button.count():
                                # A lab may supply its own visible control and hide
                                # the duplicate shared-reader control deliberately.
                                copy_button = code.locator('xpath=ancestor::*[contains(concat(" ", normalize-space(@class), " "), " codewrap ")][1]').locator('.copybtn:visible')
                            if not copy_button.count():
                                failures.append(f'{path.name}: no visible copy control for first code listing')
                            else:
                                copy_button.first.click()
                            if page.evaluate('window.__copiedCode') != expected:
                                failures.append(f'{path.name}: local clipboard fallback changed code')
                    context.close()
            index = repo / 'index.html'
            if index.exists():
                context = browser.new_context()
                context.route('http://**', lambda route: route.abort())
                context.route('https://**', lambda route: route.abort())
                page = context.new_page()
                page.goto(index.as_uri())
                page.locator('#lecture-search').fill('no_possible_course_match_923847')
                if page.locator('[data-lecture]:visible').count():
                    failures.append('index.html: search filtering failed')
                context.close()
            browser.close()
    except Exception as exc:
        detail = str(exc).splitlines()[0]
        detail = re.sub(r'[A-Za-z]:[\\/].*', '<local path>', detail)
        return {'status': 'not completed', 'reason': type(exc).__name__, 'detail': detail,
                'findings': findings, 'failures': failures}
    return {'status': 'failed' if failures else 'passed', 'findings': findings, 'failures': failures,
            'clipboard': 'Fallback branch checked with captured text; manual OS clipboard verification not performed',
            'network': 'HTTP and HTTPS requests blocked during browser checks'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--browser-executable', type=Path, help='Explicit disposable renderer; disables browser fallback')
    args = parser.parse_args()
    repo = ROOT / SLUG
    manifest = json.loads(read(repo / 'source-manifest.json'))
    report = {'course': manifest['course'], 'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope': 'Reader mechanics only; does not certify chapter or course completion',
              'static': static_checks(repo),
              'browser': browser_checks(repo, args.browser_executable) if args.browser else {'status': 'not performed', 'reason': '--browser not requested'},
              'pedagogy': {'status': 'not performed', 'reason': 'Requires chapter editorial review'},
              'python_execution': {'status': 'not performed', 'reason': 'Run declared lab/snippet checks separately'}}
    (repo / 'reader-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'static={report["static"]["status"]}, browser={report["browser"]["status"]}')
    for line in report['static']['failures'] + report['browser'].get('failures', []):
        print('FAIL', line)
    failed = report['static']['status'] == 'failed' or report['browser']['status'] in ('failed', 'not completed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
