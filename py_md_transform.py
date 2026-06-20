from html import escape
import json
import os
from pathlib import Path
import shutil
from datetime import datetime
from urllib.parse import quote

from src_lib import md_obs_parser


INDEX_IGNORED_DIRECTORIES = {"css", "js"}
SRC_LIB_DIRECTORY = "src_lib"
APP_VERSION = "0.2 | 2026-06"


def safe_display(value: object) -> str:
    return str(value).encode("ascii", errors="backslashreplace").decode("ascii")


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

    print("Directories affected by the export:")
    for directory in directories:
        print(f"- {safe_display(directory.relative_to(root))}")


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
  --link-hover-color: #0b57d0;
  --link-hover-bg: rgba(11, 87, 208, 0.08);
  --missing-color: #9a3412;
  --border-color: #ddd;
  --soft-bg: #f5f5f5;
  --mark-bg: #fff3a3;
  --quote-bg: #f8f9fb;
  --quote-border: #8aa4c8;
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
  --link-hover-color: #aecbfa;
  --link-hover-bg: rgba(138, 180, 248, 0.14);
  --missing-color: #f0a56b;
  --border-color: #3b3f45;
  --soft-bg: #20242a;
  --mark-bg: #6b5d21;
  --quote-bg: #1d2228;
  --quote-border: #6f8fbd;
  --button-bg: #252a31;
  --button-hover-bg: #303740;
  --button-border: #555d68;
}

body {
  max-width: 760px;
  margin: 40px auto;
  padding: 0 20px;
  font-family: Arial, sans-serif;
  line-height: 1.25;
  color: var(--text-color);
  background: var(--page-bg);
}

h1,
h2,
h3,
h4,
h5,
h6 {
  line-height: 1.15;
  margin: 1em 0 0.35em;
}

h1 {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.3em;
}

a {
  color: var(--link-color);
  border-radius: 3px;
  text-decoration-thickness: 1px;
  text-underline-offset: 2px;
  transition: color 120ms ease, background-color 120ms ease, text-decoration-thickness 120ms ease;
}

a:hover {
  color: var(--link-hover-color);
  background: var(--link-hover-bg);
  text-decoration-thickness: 2px;
}

.wiki-link-missing {
  color: var(--missing-color);
  border-bottom: 1px dotted var(--missing-color);
}

p {
  margin: 0 0 0.35em;
}

ul {
  margin: 0 0 0.55em 1.25em;
  padding: 0;
}

li {
  margin: 0.12em 0;
}

mark {
  padding: 0 0.15em;
  background: var(--mark-bg);
  color: inherit;
}

hr {
  margin: 1.2em 0;
  border: 0;
  border-top: 1px solid var(--border-color);
}

blockquote {
  margin: 0 0 0.7em;
  padding: 0.45em 0.75em;
  color: var(--text-color);
  background: var(--quote-bg);
  border-left: 4px solid var(--quote-border);
}

blockquote p {
  margin: 0;
}

.task-list-item {
  display: flex;
  gap: 0.35em;
  align-items: baseline;
}

.task-list-item input[type="checkbox"] {
  flex: 0 0 auto;
  transform: translateY(0.1em);
}

.math-block {
  overflow-x: auto;
  margin: 0 0 0.75em;
}

.qrcode-block {
  display: inline-block;
  margin: 0 0 0.75em;
  padding: 8px;
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
  margin: 0 0 0.7em;
  padding: 8px;
  font-family: Consolas, monospace;
  background: var(--soft-bg);
  border: 1px solid var(--border-color);
}

table {
  width: 100%;
  margin: 0 0 0.8em;
  border-collapse: collapse;
}

th,
td {
  padding: 5px 7px;
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
        mode === "dark" ? "Switch to light mode" : "Switch to dark mode"
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


def ensure_src_lib_assets(project_dir: Path, output_dir: Path) -> None:
    src_lib_dir = project_dir / SRC_LIB_DIRECTORY
    if not src_lib_dir.is_dir():
        return

    output_dir.mkdir(exist_ok=True)

    for source_path in src_lib_dir.rglob("*"):
        if "__pycache__" in source_path.parts:
            continue
        if (
            not source_path.is_file()
            or source_path.name == "index_include.html"
            or source_path.suffix == ".py"
        ):
            continue

        target_path = output_dir / source_path.relative_to(src_lib_dir)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def read_index_include(project_dir: Path) -> str:
    include_file = project_dir / SRC_LIB_DIRECTORY / "index_include.html"
    if not include_file.is_file():
        return ""

    return include_file.read_text(encoding="utf-8").strip()


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


def create_export_index(project_dir: Path, output_dir: Path, css_file: Path) -> Path:
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
    index_include = read_index_include(project_dir)
    include_html = f'<div class="index-include">{index_include}</div>\n' if index_include else ""

    html = (
        "<!doctype html>\n"
        "<html>\n"
        "<head>\n"
        '  <meta charset="utf-8">\n'
        "  <title>Exported files</title>\n"
        f'  <script src="{mode_js_href}"></script>\n'
        f'  <link rel="stylesheet" href="{css_href}">\n'
        f'  <script src="{jquery_href}"></script>\n'
        "</head>\n"
        "<body class=\"index-page\">\n"
        '<button type="button" class="mode-toggle" data-mode-toggle>dark</button>\n'
        "<h1>Exported files</h1>\n"
        f"{include_html}"
        "<p class=\"index-meta\">"
        f"The index contains {directory_count} directories and {file_count} files. "
        f"Created at {escape(created_at)}."
        "</p>\n"
        "<div class=\"index-toolbar\">"
        '<button type="button" id="toggle-all">expand all</button>'
        "</div>\n"
        f"{tree}\n"
        "<script>\n"
        "$(function () {\n"
        "  function updateToggleButton() {\n"
        "    var anyCollapsed = $('.root-directory.collapsed').length > 0;\n"
        "    $('#toggle-all').text(anyCollapsed ? 'expand all' : 'collapse all');\n"
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
    ensure_src_lib_assets(project_dir, output_dir)
    output_dir.mkdir(exist_ok=True)
    css_file = create_css_file(output_dir)
    math_js_file = create_math_js_file(output_dir)
    md_qrcode_js_file = create_qrcode_js_file(output_dir)
    mode_js_file = create_mode_js_file(output_dir)
    katex_css_file = output_dir / "js" / "katex" / "katex.min.css"
    katex_js_file = output_dir / "js" / "katex" / "katex.min.js"
    auto_render_js_file = output_dir / "js" / "katex" / "auto-render.min.js"
    qrcode_js_file = output_dir / "js" / "qrcode.js"
    wiki_link_index, ambiguous_links = md_obs_parser.build_wiki_link_index(
        link_paths or paths, source_dir, output_dir
    )

    if ambiguous_links:
        print("Ambiguous wiki links that will not be linked automatically:")
        for link in sorted(ambiguous_links):
            print(f"- {safe_display(link)}")

    for path in paths:
        relative_path = md_obs_parser.html_target_relative_path(path.relative_to(source_dir))
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
        html = md_obs_parser.markdown_to_html(
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
        print(f"Transformed: {safe_display(path)} -> {safe_display(target)}")


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
            print(f"Missing canvas helper file: {safe_display(helper_file)}")

    for path in paths:
        relative_canvas_path = path.relative_to(source_dir)
        relative_html_path = md_obs_parser.html_target_relative_path(relative_canvas_path)
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
            md_obs_parser.build_canvas_wiki_links(wiki_link_index, html_target),
        )
        html_target.write_text(html, encoding="utf-8")
        print(f"Canvas transformed: {safe_display(path)} -> {safe_display(html_target)}")


def transform_sources_to_html(
    markdown_paths: list[Path],
    canvas_paths: list[Path],
    source_dir: Path,
    project_dir: Path,
    output_dir: Path,
) -> None:
    ensure_src_lib_assets(project_dir, output_dir)
    css_file = create_css_file(output_dir)
    transform_markdown_to_html(
        markdown_paths,
        source_dir,
        project_dir,
        output_dir,
        markdown_paths + canvas_paths,
    )
    wiki_link_index, _ambiguous_links = md_obs_parser.build_wiki_link_index(
        markdown_paths + canvas_paths, source_dir, output_dir
    )
    transform_canvas_to_html(canvas_paths, source_dir, output_dir, wiki_link_index)
    index_file = create_export_index(project_dir, output_dir, css_file)
    print(f"Created index: {safe_display(index_file)}")


if __name__ == "__main__":
    project_directory = Path.cwd()
    source_directory = project_directory / "src"
    output_directory = project_directory / "html"
    markdown_files = find_markdown_files(source_directory, output_directory)
    canvas_files = find_canvas_files(source_directory, output_directory)
    source_files = markdown_files + canvas_files

    if not source_files:
        print("No *.md or *.canvas files found.")
    else:
        print(f"py_md_transform {APP_VERSION}")
        print_affected_directories(source_files, source_directory)
        answer = input("Run export? [yes/no]: ").strip().lower()

        if answer in {"yes", "y"}:
            transform_sources_to_html(
                markdown_files,
                canvas_files,
                source_directory,
                project_directory,
                output_directory,
            )
        else:
            print("Action canceled.")
