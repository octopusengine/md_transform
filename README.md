# py_md_transform

Offline Obsidian Markdown and Canvas exporter for a local notes vault.

The project reads source files from `src/` and writes a static HTML export to
`html/`. It is intentionally simple: no web service, no build server, and no
external runtime dependency for viewing the generated pages.

## Features

- Export Markdown files from `src/**/*.md` to matching `html/**/*.html` files.
- Generate a structured `html/index.html` with expandable folders.
- Convert common Markdown blocks: headings, paragraphs, tables, code blocks,
  Markdown links, bare `http(s)` URLs, and Obsidian wiki links such as
  `[[note]]` and `[[note|label]]`.
- Detect ambiguous wiki links and avoid silently creating the wrong link.
- Render math with local KaTeX files.
- Render QR code blocks with local JavaScript helpers.
- Export Obsidian Canvas files (`*.canvas`) to standalone HTML pages.
- Link `[[wiki]]`, Markdown links, and bare URLs inside Canvas text nodes.
- Link Canvas file cards when their target can be resolved in the export.
- Generate helper files such as `html/css/md.css`, `html/js/mode.js`,
  `html/js/md_math.js`, and `html/js/md_qrcode.js`.

## Project Layout

```text
src/                  Source Markdown and Canvas files
html/                 Generated static HTML export
html/css/             Generated and/or local CSS helpers
html/js/              Local JavaScript helpers and vendored libraries
py_md_transform.py    Main export script
ABOUT_py_md_trans.md  Project notes and local collaboration rules
```

## Usage

Run the exporter from the project root:

```bash
python py_md_transform.py
```

The script prints the affected source directories and asks for confirmation.
Answer `ano` or `a` to generate the export.

For non-interactive use:

```bash
printf "ano\n" | python py_md_transform.py
```

On Windows PowerShell:

```powershell
@'
ano
'@ | python py_md_transform.py
```

Open the generated export at:

```text
html/index.html
```

## Wiki Links

Wiki links are resolved against all Markdown and Canvas source files.

Examples:

```markdown
[[btc_popis]]
[[btc_popis|Bitcoin overview]]
[[folder/note]]
[[some_canvas]]
[[some_canvas.canvas]]
```

If a link name is ambiguous, the script reports it and does not guess.

## Bare URL Links

Plain external URLs in Markdown text are converted to links:

```markdown
https://example.com/page
```

The generated HTML keeps trailing punctuation such as a sentence-ending period
outside the link.

## QR Code Blocks

Use a fenced code block with the `qrcode` language:

````markdown
```qrcode
content_for_qr
```
````

The generated page renders a QR code for `content_for_qr`.

## Canvas Export

Canvas source files are copied and rendered as HTML:

```text
src/path/file.canvas       -> html/path/file.canvas
src/path/file.canvas       -> html/path/file_canvas.html
```

Canvas text nodes support:

- `[[wiki]]` links
- `[[wiki|label]]` links
- `[label](https://example.com)` Markdown links
- bare `https://example.com` URLs

Canvas file cards are linked when their `file` value resolves to a known source
Markdown or Canvas file.

## Local Assets

The export is designed to work offline. Required CSS and JavaScript helpers are
stored under `html/css/` and `html/js/`, including local KaTeX and QR code
assets.

## Development Notes

The repository includes examples under `src/tests_examples/`. They are useful
for checking wiki links, bare URLs, math, QR codes, and Canvas rendering after
changes.

Basic syntax check:

```bash
python -m py_compile py_md_transform.py
```

Full export check:

```bash
printf "ano\n" | python py_md_transform.py
```
