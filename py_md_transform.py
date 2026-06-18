from html import escape
import json
import os
from pathlib import Path
import re
import shutil
from datetime import datetime
from urllib.parse import quote


LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
AUTO_LINK_PATTERN = re.compile(r"(?<![\"'=])\bhttps?://[^\s<>()]+[^\s<>().,;:!?]")
INDEX_IGNORED_DIRECTORIES = {"css", "js"}


def safe_display(value: object) -> str:
    return str(value).encode("ascii", errors="backslashreplace").decode("ascii")


def normalize_link_key(value: str) -> str:
    return value.strip().removesuffix(".md").lower()


def html_target_relative_path(path: Path) -> Path:
    if path.suffix.lower() == ".canvas":
        return path.with_name(f"{path.stem}_canvas.html")

    return path.with_suffix(".html")


def find_markdown_files(root: Path, output_dir: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*.md")
        if path.is_file() and output_dir not in path.parents
    ]


def find_canvas_files(root: Path, output_dir: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*.canvas")
        if path.is_file() and output_dir not in path.parents
    ]


def print_affected_directories(paths: list[Path], root: Path) -> None:
    directories = sorted({path.parent for path in paths})

    print("Adresare, kterych se transformace bude tykat:")
    for directory in directories:
        print(f"- {safe_display(directory.relative_to(root))}")


def build_wiki_link_index(
    paths: list[Path],
    source_dir: Path,
    output_dir: Path,
) -> tuple[dict[str, Path], set[str]]:
    candidates: dict[str, list[Path]] = {}

    for path in paths:
        relative_path = path.relative_to(source_dir)
        target = output_dir / html_target_relative_path(relative_path)
        relative_source = path.relative_to(source_dir).with_suffix("")

        keys = {
            normalize_link_key(path.stem),
            normalize_link_key(relative_source.as_posix()),
            normalize_link_key(str(relative_source).replace("\\", "/")),
        }

        if path.suffix.lower() == ".canvas":
            canvas_relative_source = relative_source.with_name(
                f"{relative_source.name}_canvas"
            )
            keys.update(
                {
                    normalize_link_key(f"{path.stem}_canvas"),
                    normalize_link_key(f"{path.stem}.canvas"),
                    normalize_link_key(canvas_relative_source.as_posix()),
                    normalize_link_key(str(canvas_relative_source).replace("\\", "/")),
                    normalize_link_key(str(path.relative_to(source_dir)).replace("\\", "/")),
                }
            )

        for key in keys:
            candidates.setdefault(key, []).append(target)

    link_index: dict[str, Path] = {}
    ambiguous_links: set[str] = set()

    for key, targets in candidates.items():
        unique_targets = sorted(set(targets))
        if len(unique_targets) == 1:
            link_index[key] = unique_targets[0]
        else:
            ambiguous_links.add(key)

    return link_index, ambiguous_links


def transform_inline_markdown(
    text: str,
    wiki_link_index: dict[str, Path],
    current_target: Path,
) -> str:
    escaped_text = escape(text)

    def replace_link(match: re.Match[str]) -> str:
        label = match.group(1)
        url = match.group(2)
        return f'<a href="{url}">{label}</a>'

    def replace_wiki_link(match: re.Match[str]) -> str:
        raw_link = match.group(1).strip()
        link_target, _, label = raw_link.partition("|")
        label = label.strip() or link_target.strip()
        key = normalize_link_key(link_target)
        target = wiki_link_index.get(key)

        if target is None:
            return f'<span class="wiki-link-missing">{escape(label)}</span>'

        href = os.path.relpath(target, start=current_target.parent).replace("\\", "/")
        return f'<a href="{escape(href)}">{escape(label)}</a>'

    def replace_auto_link(match: re.Match[str]) -> str:
        url = match.group(0)
        safe_url = escape(url, quote=True)
        return f'<a href="{safe_url}">{safe_url}</a>'

    def auto_link_text_segments(value: str) -> str:
        segments = re.split(r"(<a\b[^>]*>.*?</a>)", value, flags=re.IGNORECASE)
        return "".join(
            segment
            if segment.lower().startswith("<a")
            else AUTO_LINK_PATTERN.sub(replace_auto_link, segment)
            for segment in segments
        )

    html = LINK_PATTERN.sub(replace_link, escaped_text)
    html = WIKI_LINK_PATTERN.sub(replace_wiki_link, html)
    return auto_link_text_segments(html)


def build_canvas_wiki_links(
    wiki_link_index: dict[str, Path],
    current_target: Path,
) -> dict[str, str]:
    return {
        key: os.path.relpath(target, start=current_target.parent).replace("\\", "/")
        for key, target in wiki_link_index.items()
    }


def is_table_row(line: str) -> bool:
    stripped_line = line.strip()
    return stripped_line.startswith("|") and stripped_line.endswith("|")


def is_table_separator(line: str) -> bool:
    if not is_table_row(line):
        return False

    cells = parse_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def parse_table_row(line: str) -> list[str]:
    stripped_line = line.strip()
    if stripped_line.startswith("|"):
        stripped_line = stripped_line[1:]
    if stripped_line.endswith("|"):
        stripped_line = stripped_line[:-1]

    return [cell.strip() for cell in stripped_line.split("|")]


def render_table(
    headers: list[str],
    rows: list[list[str]],
    wiki_link_index: dict[str, Path],
    current_target: Path,
) -> str:
    header_cells = "".join(
        f"<th>{transform_inline_markdown(header, wiki_link_index, current_target)}</th>"
        for header in headers
    )
    table_lines = ["<table>", "<thead>", f"<tr>{header_cells}</tr>", "</thead>"]

    if rows:
        table_lines.append("<tbody>")
        for row in rows:
            normalized_row = row[: len(headers)] + [""] * max(0, len(headers) - len(row))
            body_cells = "".join(
                f"<td>{transform_inline_markdown(cell, wiki_link_index, current_target)}</td>"
                for cell in normalized_row
            )
            table_lines.append(f"<tr>{body_cells}</tr>")
        table_lines.append("</tbody>")

    table_lines.append("</table>")
    return "\n".join(table_lines)


def render_qrcode_block(text: str) -> str:
    qrcode_json = json.dumps(text, ensure_ascii=False).replace("</", "<\\/")
    return (
        '<div class="qrcode-block">'
        '<div class="qrcode-output" aria-label="QR code"></div>'
        '<script type="application/json" class="qrcode-data">'
        f"{qrcode_json}"
        "</script>"
        '<noscript><pre class="qrcode-source">'
        f"{escape(text)}"
        "</pre></noscript>"
        "</div>"
    )


def markdown_to_html(
    markdown: str,
    page_title: str,
    css_href: str,
    mode_js_href: str,
    katex_css_href: str,
    katex_js_href: str,
    auto_render_js_href: str,
    math_js_href: str,
    qrcode_js_href: str,
    md_qrcode_js_href: str,
    wiki_link_index: dict[str, Path],
    current_target: Path,
) -> str:
    lines = markdown.splitlines()
    html_lines: list[str] = [f"<h1>{escape(page_title)}</h1>"]
    in_code_block = False
    code_block_language = ""
    code_lines: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped_line = line.strip()

        if stripped_line.startswith("```"):
            if in_code_block:
                code = "\n".join(code_lines)
                if code_block_language == "qrcode":
                    html_lines.append(render_qrcode_block(code))
                else:
                    html_lines.append(f"<code>{escape(code)}</code>")
                code_lines = []
                code_block_language = ""
                in_code_block = False
            else:
                in_code_block = True
                code_block_info = stripped_line[3:].strip().split(maxsplit=1)
                code_block_language = code_block_info[0].lower() if code_block_info else ""
                code_lines = []
            index += 1
            continue

        if in_code_block:
            code_lines.append(line)
            index += 1
            continue

        if not stripped_line:
            index += 1
            continue

        if stripped_line == "$$":
            math_lines: list[str] = []
            index += 1

            while index < len(lines) and lines[index].strip() != "$$":
                math_lines.append(lines[index])
                index += 1

            if index < len(lines) and lines[index].strip() == "$$":
                index += 1

            math = escape("\n".join(math_lines))
            html_lines.append(f'<div class="math-block">$$\n{math}\n$$</div>')
            continue

        next_index = index + 1
        while next_index < len(lines) and not lines[next_index].strip():
            next_index += 1

        if (
            is_table_row(line)
            and next_index < len(lines)
            and is_table_separator(lines[next_index])
        ):
            headers = parse_table_row(line)
            rows: list[list[str]] = []
            index = next_index + 1

            while index < len(lines):
                if not lines[index].strip():
                    index += 1
                    continue
                if not is_table_row(lines[index]):
                    break
                rows.append(parse_table_row(lines[index]))
                index += 1

            html_lines.append(render_table(headers, rows, wiki_link_index, current_target))
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped_line)
        if heading_match:
            level = len(heading_match.group(1))
            content = transform_inline_markdown(
                heading_match.group(2), wiki_link_index, current_target
            )
            html_lines.append(f"<h{level}>{content}</h{level}>")
            index += 1
            continue

        content = transform_inline_markdown(stripped_line, wiki_link_index, current_target)
        html_lines.append(f"<p>{content}</p>")
        index += 1

    if in_code_block:
        code = "\n".join(code_lines)
        if code_block_language == "qrcode":
            html_lines.append(render_qrcode_block(code))
        else:
            html_lines.append(f"<code>{escape(code)}</code>")

    body = "\n".join(html_lines)
    return (
        "<!doctype html>\n"
        "<html>\n"
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>{escape(page_title)}</title>\n"
        f'  <script src="{mode_js_href}"></script>\n'
        f'  <link rel="stylesheet" href="{css_href}">\n'
        f'  <link rel="stylesheet" href="{katex_css_href}">\n'
        f'  <script defer src="{katex_js_href}"></script>\n'
        f'  <script defer src="{auto_render_js_href}"></script>\n'
        f'  <script defer src="{math_js_href}"></script>\n'
        f'  <script defer src="{qrcode_js_href}"></script>\n'
        f'  <script defer src="{md_qrcode_js_href}"></script>\n'
        "</head>\n"
        "<body>\n"
        '<button type="button" class="mode-toggle" data-mode-toggle>dark</button>\n'
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def canvas_to_html(
    canvas_json: str,
    page_title: str,
    light_css_href: str,
    canvas_css_href: str,
    canvas_js_href: str,
    canvas_data_href: str,
    wiki_links: dict[str, str],
) -> str:
    canvas_data = json.loads(canvas_json)
    fallback_json = json.dumps(canvas_data, ensure_ascii=False, indent=2).replace(
        "</", "<\\/"
    )
    wiki_links_json = json.dumps(wiki_links, ensure_ascii=False, indent=2).replace(
        "</", "<\\/"
    )

    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{escape(page_title)}</title>\n"
        f'  <link id="theme-stylesheet" rel="stylesheet" href="{light_css_href}">\n'
        f'  <link rel="stylesheet" href="{canvas_css_href}">\n'
        "</head>\n"
        "<body>\n"
        '  <button id="theme-toggle" class="theme-toggle" type="button" '
        'aria-label="Switch color theme">dark</button>\n'
        "  <main class=\"canvas-shell\">\n"
        '    <div id="canvas" class="canvas" aria-label="Rendered Obsidian canvas"></div>\n'
        "  </main>\n"
        '  <script type="application/json" id="fallback-canvas-data">\n'
        f"{fallback_json}\n"
        "  </script>\n"
        '  <script type="application/json" id="canvas-wiki-links">\n'
        f"{wiki_links_json}\n"
        "  </script>\n"
        f'  <script src="{canvas_js_href}"></script>\n'
        "  <script>\n"
        "    const wikiLinksElement = document.getElementById(\"canvas-wiki-links\");\n"
        "    const wikiLinks = wikiLinksElement ? JSON.parse(wikiLinksElement.textContent) : {};\n"
        "    const themeStylesheet = document.getElementById(\"theme-stylesheet\");\n"
        "    const themeToggle = document.getElementById(\"theme-toggle\");\n"
        "\n"
        "    function setTheme(theme) {\n"
        "      themeStylesheet.href = themeStylesheet.href.replace(/css\\/(light|dark)\\.css$/, `css/${theme}.css`);\n"
        "      themeToggle.textContent = theme === \"dark\" ? \"light\" : \"dark\";\n"
        "      themeToggle.setAttribute(\"aria-pressed\", theme === \"dark\");\n"
        "      localStorage.setItem(\"obsidian-canvas-theme\", theme);\n"
        "    }\n"
        "\n"
        "    const savedTheme = localStorage.getItem(\"obsidian-canvas-theme\") || \"light\";\n"
        "    setTheme(savedTheme);\n"
        "\n"
        "    themeToggle.addEventListener(\"click\", () => {\n"
        "      const isDark = /css\\/dark\\.css$/.test(themeStylesheet.getAttribute(\"href\"));\n"
        "      setTheme(isDark ? \"light\" : \"dark\");\n"
        "    });\n"
        "\n"
        "    ObsidianCanvas\n"
        f"      .loadCanvasData({json.dumps(canvas_data_href)})\n"
        "      .then((data) => ObsidianCanvas.renderCanvas(data, { wikiLinks }));\n"
        "  </script>\n"
        "</body>\n"
        "</html>\n"
    )


def create_css_file(output_dir: Path) -> Path:
    css_file = output_dir / "css" / "md.css"
    css_file.parent.mkdir(exist_ok=True)
    css_file.write_text(
        """:root {
  color-scheme: light;
  --page-bg: #fff;
  --text-color: #222;
  --muted-color: #555;
  --link-color: #0645ad;
  --missing-color: #9a3412;
  --border-color: #ddd;
  --soft-bg: #f5f5f5;
  --button-bg: #f5f5f5;
  --button-hover-bg: #eaeaea;
  --button-border: #bbb;
}

:root[data-mode="dark"] {
  color-scheme: dark;
  --page-bg: #151719;
  --text-color: #e7e3dc;
  --muted-color: #afa89f;
  --link-color: #8ab4f8;
  --missing-color: #f0a56b;
  --border-color: #3b3f45;
  --soft-bg: #20242a;
  --button-bg: #252a31;
  --button-hover-bg: #303740;
  --button-border: #555d68;
}

body {
  max-width: 760px;
  margin: 40px auto;
  padding: 0 20px;
  font-family: Arial, sans-serif;
  line-height: 1.6;
  color: var(--text-color);
  background: var(--page-bg);
}

h1,
h2,
h3,
h4,
h5,
h6 {
  line-height: 1.25;
  margin: 1.4em 0 0.5em;
}

h1 {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.3em;
}

a {
  color: var(--link-color);
}

.wiki-link-missing {
  color: var(--missing-color);
  border-bottom: 1px dotted var(--missing-color);
}

p {
  margin: 0 0 1em;
}

.math-block {
  overflow-x: auto;
  margin: 0 0 1.5em;
}

.qrcode-block {
  display: inline-block;
  margin: 0 0 1.5em;
  padding: 12px;
  background: #fff;
  border: 1px solid var(--border-color);
}

.qrcode-output {
  width: 192px;
  height: 192px;
}

.qrcode-output img,
.qrcode-output canvas {
  display: block;
}

code {
  display: block;
  white-space: pre-wrap;
  margin: 0 0 1em;
  padding: 12px;
  font-family: Consolas, monospace;
  background: var(--soft-bg);
  border: 1px solid var(--border-color);
}

table {
  width: 100%;
  margin: 0 0 1.5em;
  border-collapse: collapse;
}

th,
td {
  padding: 8px 10px;
  text-align: left;
  border: 1px solid var(--border-color);
}

th {
  background: var(--soft-bg);
}

.mode-toggle {
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: 10;
  min-width: 58px;
  padding: 6px 10px;
  color: var(--text-color);
  background: var(--button-bg);
  border: 1px solid var(--button-border);
  cursor: pointer;
}

.mode-toggle:hover {
  background: var(--button-hover-bg);
}

.index-page ul {
  margin: 0 0 0 1.2em;
  padding: 0;
  list-style: none;
}

.index-page li {
  margin: 0.25em 0;
}

.directory-label {
  font-weight: 700;
}

.directory-label::before {
  content: "\\1F4C1  ";
}

.file-link::before {
  content: "\\1F4C4  ";
}

.index-meta {
  margin: -0.5em 0 1em;
  color: var(--muted-color);
}

.index-toolbar {
  margin: 0 0 1.25em;
}

.index-toolbar button {
  padding: 6px 10px;
  color: var(--text-color);
  background: var(--button-bg);
  border: 1px solid var(--button-border);
  cursor: pointer;
}

.index-toolbar button:hover {
  background: var(--button-hover-bg);
}

.root-directory > .directory-label {
  cursor: pointer;
}

.root-directory > .directory-label::after {
  content: " \\25BE";
  color: var(--muted-color);
}

.root-directory.collapsed > .directory-label::after {
  content: " \\25B8";
}

.root-directory.collapsed > ul {
  display: none;
}
""",
        encoding="utf-8",
    )
    return css_file


def create_math_js_file(output_dir: Path) -> Path:
    js_file = output_dir / "js" / "md_math.js"
    js_file.parent.mkdir(exist_ok=True)
    js_file.write_text(
        """document.addEventListener("DOMContentLoaded", function () {
  if (!window.renderMathInElement) {
    return;
  }

  renderMathInElement(document.body, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "$", right: "$", display: false }
    ],
    ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code"]
  });
});
""",
        encoding="utf-8",
    )
    return js_file


def create_qrcode_js_file(output_dir: Path) -> Path:
    js_file = output_dir / "js" / "md_qrcode.js"
    js_file.parent.mkdir(exist_ok=True)
    js_file.write_text(
        """document.addEventListener("DOMContentLoaded", function () {
  if (!window.QRCode) {
    return;
  }

  document.querySelectorAll(".qrcode-block").forEach(function (block) {
    var data = block.querySelector(".qrcode-data");
    var output = block.querySelector(".qrcode-output");

    if (!data || !output) {
      return;
    }

    var text = "";
    try {
      text = JSON.parse(data.textContent);
    } catch (error) {
      text = data.textContent;
    }

    output.innerHTML = "";
    new QRCode(output, {
      text: text,
      width: 192,
      height: 192,
      correctLevel: QRCode.CorrectLevel.M
    });
  });
});
""",
        encoding="utf-8",
    )
    return js_file


def create_mode_js_file(output_dir: Path) -> Path:
    js_file = output_dir / "js" / "mode.js"
    js_file.parent.mkdir(exist_ok=True)
    js_file.write_text(
        """(function () {
  var storageKey = "md-export-mode";

  function savedMode() {
    try {
      return localStorage.getItem(storageKey);
    } catch (error) {
      return null;
    }
  }

  function rememberMode(mode) {
    try {
      localStorage.setItem(storageKey, mode);
    } catch (error) {
      return;
    }
  }

  function preferredMode() {
    var mode = savedMode();
    if (mode === "dark" || mode === "light") {
      return mode;
    }

    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }

    return "light";
  }

  function updateButtons(mode) {
    document.querySelectorAll("[data-mode-toggle]").forEach(function (button) {
      button.textContent = mode === "dark" ? "light" : "dark";
      button.setAttribute(
        "aria-label",
        mode === "dark" ? "Přepnout na světlý režim" : "Přepnout na tmavý režim"
      );
    });
  }

  function setMode(mode) {
    document.documentElement.setAttribute("data-mode", mode);
    rememberMode(mode);
    updateButtons(mode);
  }

  setMode(preferredMode());

  document.addEventListener("DOMContentLoaded", function () {
    updateButtons(document.documentElement.getAttribute("data-mode") || preferredMode());

    document.querySelectorAll("[data-mode-toggle]").forEach(function (button) {
      button.addEventListener("click", function () {
        var currentMode = document.documentElement.getAttribute("data-mode") || preferredMode();
        setMode(currentMode === "dark" ? "light" : "dark");
      });
    });
  });
})();
""",
        encoding="utf-8",
    )
    return js_file


def sort_paths(paths: list[Path]) -> list[Path]:
    return sorted(paths, key=lambda path: path.name.casefold())


def html_href(path: Path) -> str:
    return quote(path.as_posix(), safe="/-_.~")


def is_indexed_path(path: Path, output_dir: Path) -> bool:
    relative_parts = path.relative_to(output_dir).parts
    return not relative_parts or relative_parts[0].lower() not in INDEX_IGNORED_DIRECTORIES


def is_export_html_file(path: Path, output_dir: Path) -> bool:
    if not path.is_file() or path.suffix.lower() != ".html":
        return False

    relative_path = path.relative_to(output_dir)
    if len(relative_path.parts) == 1 and path.stem.lower().startswith("index"):
        return False

    return is_indexed_path(path, output_dir)


def count_export_items(output_dir: Path) -> tuple[int, int]:
    directory_count = sum(
        1
        for path in output_dir.rglob("*")
        if path.is_dir() and is_indexed_path(path, output_dir)
    )
    file_count = sum(
        1
        for path in output_dir.rglob("*.html")
        if is_export_html_file(path, output_dir)
    )
    return directory_count, file_count


def render_index_tree(directory: Path, output_dir: Path, depth: int = 0) -> str:
    list_class = ' class="export-tree"' if depth == 0 else ""
    lines = [f"<ul{list_class}>"]
    child_directories = sort_paths(
        [
            path
            for path in directory.iterdir()
            if path.is_dir() and is_indexed_path(path, output_dir)
        ]
    )
    html_files = sort_paths(
        [
            path
            for path in directory.iterdir()
            if is_export_html_file(path, output_dir)
        ]
    )

    for child_directory in child_directories:
        item_class = ' class="root-directory collapsed"' if depth == 0 else ""
        lines.append(
            f"<li{item_class}>"
            f'<span class="directory-label">{escape(child_directory.name)}</span>'
        )
        lines.append(render_index_tree(child_directory, output_dir, depth + 1))
        lines.append("</li>")

    for html_file in html_files:
        relative_path = html_file.relative_to(output_dir)
        href = html_href(relative_path)
        lines.append(
            f'<li><a class="file-link" href="{escape(href)}">{escape(html_file.name)}</a></li>'
        )

    lines.append("</ul>")
    return "\n".join(lines)


def create_export_index(output_dir: Path, css_file: Path) -> Path:
    index_file = output_dir / "index.html"
    css_href = os.path.relpath(css_file, start=index_file.parent).replace("\\", "/")
    mode_js_file = create_mode_js_file(output_dir)
    mode_js_href = os.path.relpath(mode_js_file, start=index_file.parent).replace(
        "\\", "/"
    )
    jquery_file = output_dir / "js" / "jquery.min.js"
    jquery_href = os.path.relpath(jquery_file, start=index_file.parent).replace("\\", "/")
    directory_count, file_count = count_export_items(output_dir)
    created_at = datetime.now().strftime("%Y-%m-%d | %H:%M")
    tree = render_index_tree(output_dir, output_dir)

    html = (
        "<!doctype html>\n"
        "<html>\n"
        "<head>\n"
        '  <meta charset="utf-8">\n'
        "  <title>Exportovane soubory</title>\n"
        f'  <script src="{mode_js_href}"></script>\n'
        f'  <link rel="stylesheet" href="{css_href}">\n'
        f'  <script src="{jquery_href}"></script>\n'
        "</head>\n"
        "<body class=\"index-page\">\n"
        '<button type="button" class="mode-toggle" data-mode-toggle>dark</button>\n'
        "<h1>Exportovane soubory</h1>\n"
        "<p class=\"index-meta\">"
        f"Index obsahuje {directory_count} adresářů a celkem {file_count} souborů. "
        f"Byl vytvořen {escape(created_at)}."
        "</p>\n"
        "<div class=\"index-toolbar\">"
        '<button type="button" id="toggle-all">rozbalit vše</button>'
        "</div>\n"
        f"{tree}\n"
        "<script>\n"
        "$(function () {\n"
        "  function updateToggleButton() {\n"
        "    var anyCollapsed = $('.root-directory.collapsed').length > 0;\n"
        "    $('#toggle-all').text(anyCollapsed ? 'rozbalit vše' : 'sbalit vše');\n"
        "  }\n"
        "\n"
        "  $('.root-directory > .directory-label').on('click', function () {\n"
        "    var item = $(this).closest('.root-directory');\n"
        "    item.toggleClass('collapsed');\n"
        "    item.children('ul').stop(true, true).slideToggle(120);\n"
        "    updateToggleButton();\n"
        "  });\n"
        "\n"
        "  $('#toggle-all').on('click', function () {\n"
        "    var rootDirectories = $('.root-directory');\n"
        "    var anyCollapsed = rootDirectories.filter('.collapsed').length > 0;\n"
        "\n"
        "    if (anyCollapsed) {\n"
        "      rootDirectories.removeClass('collapsed').children('ul').stop(true, true).slideDown(120);\n"
        "    } else {\n"
        "      rootDirectories.addClass('collapsed').children('ul').stop(true, true).slideUp(120);\n"
        "    }\n"
        "\n"
        "    updateToggleButton();\n"
        "  });\n"
        "\n"
        "  updateToggleButton();\n"
        "});\n"
        "</script>\n"
        "</body>\n"
        "</html>\n"
    )
    index_file.write_text(html, encoding="utf-8")
    return index_file


def transform_markdown_to_html(
    paths: list[Path],
    source_dir: Path,
    project_dir: Path,
    output_dir: Path,
    link_paths: list[Path] | None = None,
) -> None:
    output_dir.mkdir(exist_ok=True)
    css_file = create_css_file(output_dir)
    math_js_file = create_math_js_file(output_dir)
    md_qrcode_js_file = create_qrcode_js_file(output_dir)
    mode_js_file = create_mode_js_file(output_dir)
    katex_css_file = output_dir / "js" / "katex" / "katex.min.css"
    katex_js_file = output_dir / "js" / "katex" / "katex.min.js"
    auto_render_js_file = output_dir / "js" / "katex" / "auto-render.min.js"
    qrcode_js_file = output_dir / "js" / "qrcode.js"
    wiki_link_index, ambiguous_links = build_wiki_link_index(
        link_paths or paths, source_dir, output_dir
    )

    if ambiguous_links:
        print("Nejednoznacne wiki odkazy, ktere nebudou automaticky propojene:")
        for link in sorted(ambiguous_links):
            print(f"- {safe_display(link)}")

    for path in paths:
        relative_path = html_target_relative_path(path.relative_to(source_dir))
        target = output_dir / relative_path
        css_href = os.path.relpath(css_file, start=target.parent).replace("\\", "/")
        mode_js_href = os.path.relpath(mode_js_file, start=target.parent).replace(
            "\\", "/"
        )
        katex_css_href = os.path.relpath(katex_css_file, start=target.parent).replace(
            "\\", "/"
        )
        katex_js_href = os.path.relpath(katex_js_file, start=target.parent).replace(
            "\\", "/"
        )
        auto_render_js_href = os.path.relpath(
            auto_render_js_file, start=target.parent
        ).replace("\\", "/")
        math_js_href = os.path.relpath(math_js_file, start=target.parent).replace("\\", "/")
        qrcode_js_href = os.path.relpath(qrcode_js_file, start=target.parent).replace(
            "\\", "/"
        )
        md_qrcode_js_href = os.path.relpath(
            md_qrcode_js_file, start=target.parent
        ).replace("\\", "/")

        target.parent.mkdir(parents=True, exist_ok=True)
        html = markdown_to_html(
            path.read_text(encoding="utf-8"),
            path.stem,
            css_href,
            mode_js_href,
            katex_css_href,
            katex_js_href,
            auto_render_js_href,
            math_js_href,
            qrcode_js_href,
            md_qrcode_js_href,
            wiki_link_index,
            target,
        )
        target.write_text(html, encoding="utf-8")
        print(f"Transformovano: {safe_display(path)} -> {safe_display(target)}")


def transform_canvas_to_html(
    paths: list[Path],
    source_dir: Path,
    output_dir: Path,
    wiki_link_index: dict[str, Path],
) -> None:
    light_css_file = output_dir / "css" / "light.css"
    canvas_css_file = output_dir / "css" / "canvas.css"
    canvas_js_file = output_dir / "js" / "obsidian_canvas.js"

    for helper_file in [light_css_file, canvas_css_file, canvas_js_file]:
        if not helper_file.exists():
            print(f"Chybi canvas pomocny soubor: {safe_display(helper_file)}")

    for path in paths:
        relative_canvas_path = path.relative_to(source_dir)
        relative_html_path = html_target_relative_path(relative_canvas_path)
        canvas_target = output_dir / relative_canvas_path
        html_target = output_dir / relative_html_path

        light_css_href = os.path.relpath(light_css_file, start=html_target.parent).replace(
            "\\", "/"
        )
        canvas_css_href = os.path.relpath(canvas_css_file, start=html_target.parent).replace(
            "\\", "/"
        )
        canvas_js_href = os.path.relpath(canvas_js_file, start=html_target.parent).replace(
            "\\", "/"
        )
        canvas_data_href = os.path.relpath(canvas_target, start=html_target.parent).replace(
            "\\", "/"
        )

        canvas_target.parent.mkdir(parents=True, exist_ok=True)
        html_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, canvas_target)
        html = canvas_to_html(
            path.read_text(encoding="utf-8"),
            path.stem,
            light_css_href,
            canvas_css_href,
            canvas_js_href,
            canvas_data_href,
            build_canvas_wiki_links(wiki_link_index, html_target),
        )
        html_target.write_text(html, encoding="utf-8")
        print(f"Canvas transformovan: {safe_display(path)} -> {safe_display(html_target)}")


def transform_sources_to_html(
    markdown_paths: list[Path],
    canvas_paths: list[Path],
    source_dir: Path,
    project_dir: Path,
    output_dir: Path,
) -> None:
    css_file = create_css_file(output_dir)
    transform_markdown_to_html(
        markdown_paths,
        source_dir,
        project_dir,
        output_dir,
        markdown_paths + canvas_paths,
    )
    wiki_link_index, _ambiguous_links = build_wiki_link_index(
        markdown_paths + canvas_paths, source_dir, output_dir
    )
    transform_canvas_to_html(canvas_paths, source_dir, output_dir, wiki_link_index)
    index_file = create_export_index(output_dir, css_file)
    print(f"Vytvoren index: {safe_display(index_file)}")


if __name__ == "__main__":
    project_directory = Path.cwd()
    source_directory = project_directory / "src"
    output_directory = project_directory / "html"
    markdown_files = find_markdown_files(source_directory, output_directory)
    canvas_files = find_canvas_files(source_directory, output_directory)
    source_files = markdown_files + canvas_files

    if not source_files:
        print("Nebyly nalezeny zadne soubory *.md ani *.canvas.")
    else:
        print_affected_directories(source_files, source_directory)
        answer = input("Spustit transformaci? [ano/ne]: ").strip().lower()

        if answer in {"ano", "a"}:
            transform_sources_to_html(
                markdown_files,
                canvas_files,
                source_directory,
                project_directory,
                output_directory,
            )
        else:
            print("Akce zrusena.")
