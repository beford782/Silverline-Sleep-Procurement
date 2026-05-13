#!/usr/bin/env python3
"""
Generate PDF versions of the onboarding documents.

Usage:
    python tools/md_to_pdf.py            # build all (default)
    python tools/md_to_pdf.py guide      # just customer guide
    python tools/md_to_pdf.py runbook    # just internal runbook
    python tools/md_to_pdf.py drive      # just Drive folder README

Outputs to onboarding/*.pdf
"""
import os
import sys
import markdown
from weasyprint import HTML, CSS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONBOARDING = os.path.join(REPO_ROOT, 'onboarding')

# ---------------------------------------------------------------------------
# Documents to render
# ---------------------------------------------------------------------------
# kind:
#   'md'  -> render markdown to HTML, themed
#   'txt' -> render as preformatted monospaced text (preserves the original
#            ASCII layout of README-style files)
DOCS = {
    'guide': {
        'src': os.path.join(ONBOARDING, 'Onboarding_Guide.md'),
        'out': os.path.join(ONBOARDING, 'DreamFinder_Onboarding_Guide.pdf'),
        'kind': 'md',
        'header_left': 'DreamFinder Onboarding',
    },
    'runbook': {
        'src': os.path.join(ONBOARDING, 'Build_Runbook.md'),
        'out': os.path.join(ONBOARDING, 'DreamFinder_Build_Runbook.pdf'),
        'kind': 'md',
        'header_left': 'DreamFinder Build Runbook (Internal)',
    },
    'drive': {
        'src': os.path.join(ONBOARDING, 'Drive_Folder_README.txt'),
        'out': os.path.join(ONBOARDING, 'DreamFinder_Image_Upload_Guide.pdf'),
        'kind': 'txt',
        'header_left': 'DreamFinder Image Upload Guide',
    },
}


def base_css(header_left):
    return f"""
@page {{
  size: Letter;
  margin: 0.75in;
  @bottom-right {{
    content: "Page " counter(page) " of " counter(pages);
    font-family: 'Helvetica', sans-serif;
    font-size: 9pt;
    color: #888;
  }}
  @bottom-left {{
    content: "{header_left}";
    font-family: 'Helvetica', sans-serif;
    font-size: 9pt;
    color: #888;
  }}
}}
body {{
  font-family: 'Helvetica', 'Arial', sans-serif;
  font-size: 10.5pt;
  line-height: 1.5;
  color: #1a1a1a;
}}
h1 {{
  font-size: 22pt;
  color: #0f1f33;
  border-bottom: 3px solid #d4a84b;
  padding-bottom: 0.3em;
  margin-top: 0;
}}
h2 {{
  font-size: 15pt;
  color: #0f1f33;
  margin-top: 1.5em;
  border-bottom: 1px solid #ddd;
  padding-bottom: 0.2em;
}}
h3 {{
  font-size: 12pt;
  color: #1f3a5c;
  margin-top: 1.2em;
}}
hr {{
  border: none;
  border-top: 1px solid #ccc;
  margin: 1.5em 0;
}}
a {{ color: #1f3a5c; text-decoration: none; }}
code {{
  background: #f4f1e8;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 9.5pt;
  color: #8B1A1A;
}}
pre {{
  background: #f4f1e8;
  padding: 0.75em;
  border-radius: 6px;
  border-left: 3px solid #d4a84b;
  font-size: 9pt;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}}
pre code {{ background: none; padding: 0; color: #1a1a1a; }}
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 0.75em 0;
  font-size: 10pt;
}}
th, td {{
  border: 1px solid #ccc;
  padding: 0.5em 0.7em;
  text-align: left;
  vertical-align: top;
}}
th {{
  background: #0f1f33;
  color: #fff;
  font-weight: 600;
}}
tr:nth-child(even) td {{ background: #fafaf6; }}
ul, ol {{ padding-left: 1.5em; }}
li {{ margin-bottom: 0.25em; }}
blockquote {{
  border-left: 3px solid #d4a84b;
  background: #fefcf6;
  padding: 0.5em 1em;
  margin: 1em 0;
  color: #555;
  font-style: italic;
}}
strong {{ color: #0f1f33; }}
"""


def render_md(src, header_left):
    with open(src, 'r', encoding='utf-8') as f:
        md_text = f.read()
    html_body = markdown.markdown(
        md_text,
        extensions=['extra', 'sane_lists', 'tables', 'fenced_code'],
    )
    html_doc = f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"
    return html_doc, base_css(header_left)


def render_txt(src, header_left):
    """Render a structured plain-text README as a styled PDF.
    Preserves the existing ASCII layout via a single <pre> block, but
    detects underlined section headings (==== / ----) and styles them."""
    with open(src, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    # Walk lines looking for heading patterns. Markdown's setext headings
    # already use === / --- under text — feed it through markdown for nice
    # heading + paragraph styling, but keep the indented blocks as <pre>.
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < len(lines) else ''
        # Setext heading: text followed by === or ---
        if next_line and (set(next_line) == {'='} or set(next_line) == {'-'}) and len(next_line) >= 3 and line.strip():
            level = '#' if '=' in next_line else '##'
            out_lines.append(f"{level} {line.strip()}")
            i += 2
            continue
        # Indented block (2+ spaces) → preserve as code block lines
        if line.startswith('  '):
            block = []
            while i < len(lines) and (lines[i].startswith('  ') or lines[i] == ''):
                block.append(lines[i])
                i += 1
            # Strip trailing blanks
            while block and block[-1] == '':
                block.pop()
            if block:
                out_lines.append('```')
                out_lines.extend(block)
                out_lines.append('```')
            continue
        out_lines.append(line)
        i += 1

    md_text = '\n'.join(out_lines)
    html_body = markdown.markdown(md_text, extensions=['extra', 'fenced_code'])
    html_doc = f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"
    return html_doc, base_css(header_left)


def build_one(key):
    cfg = DOCS[key]
    if cfg['kind'] == 'md':
        html_doc, css = render_md(cfg['src'], cfg['header_left'])
    else:
        html_doc, css = render_txt(cfg['src'], cfg['header_left'])
    HTML(string=html_doc, base_url=os.path.dirname(cfg['src'])).write_pdf(
        cfg['out'], stylesheets=[CSS(string=css)],
    )
    size_kb = os.path.getsize(cfg['out']) / 1024
    print(f"  {os.path.basename(cfg['out'])}  ({size_kb:.0f} KB)")


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(DOCS.keys())
    invalid = [t for t in targets if t not in DOCS]
    if invalid:
        print(f"Unknown target(s): {invalid}. Valid: {list(DOCS.keys())}")
        sys.exit(1)
    print("Building PDFs:")
    for t in targets:
        build_one(t)


if __name__ == '__main__':
    main()
