from html import escape
import json
import os
from pathlib import Path
import re


LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
AUTO_LINK_PATTERN = re.compile(r"(?<![\"'=])\bhttps?://[^\s<>()]+[^\s<>().,;:!?]")
TASK_ITEM_PATTERN = re.compile(r"^-\s+\[([ xX])\](?:\s+(.*))?$")
UNORDERED_LIST_ITEM_PATTERN = re.compile(r"^-\s+(?!\[[ xX]\](?:\s|$))(.+)$")
CALLOUT_PATTERN = re.compile(r"^\[!([A-Za-z]+)\][+-]?\s*(.*)$")
CALLOUT_TYPES = {
    "note",
    "abstract",
    "info",
    "todo",
    "tip",
    "success",
    "question",
    "warning",
    "failure",
    "danger",
    "bug",
    "example",
    "quote",
}
CHRONOS_COLORS = {"red", "orange", "yellow", "green", "blue", "purple", "pink", "cyan"}
CHRONOS_ITEM_PATTERN = re.compile(r"^\s*([-@*=~])\s+\[([^\]]+)\]\s*(.*)$")
CHRONOS_COLOR_PATTERN = re.compile(
    r"^(?:#|\$)([A-Za-z]+|[0-9A-Fa-f]{3,8})(?=\s|$)\s*"
)
CHRONOS_GROUP_PATTERN = re.compile(r"^\{([^}]+)\}\s*")


def normalize_link_key(value: str) -> str:
    return value.strip().removesuffix(".md").lower()


def html_target_relative_path(path: Path) -> Path:
    if path.suffix.lower() == ".canvas":
        return path.with_name(f"{path.stem}_canvas.html")

    return path.with_suffix(".html")


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

    def apply_basic_inline_styles(value: str) -> str:
        value = re.sub(r"==(.+?)==", r"<mark>\1</mark>", value)
        value = re.sub(
            r"(?<!\*)\*\*\*(?!\s)(.+?)(?<!\s)\*\*\*(?!\*)",
            r"<strong><em>\1</em></strong>",
            value,
        )
        value = re.sub(
            r"(?<!\*)\*\*(?!\s)(.+?)(?<!\s)\*\*(?!\*)",
            r"<strong>\1</strong>",
            value,
        )
        value = re.sub(
            r"(?<!\*)\*(?![\s*])(.+?)(?<![\s*])\*(?!\*)",
            r"<em>\1</em>",
            value,
        )
        return value

    def style_text_segments(value: str) -> str:
        segments = re.split(r"(<a\b[^>]*>.*?</a>)", value, flags=re.IGNORECASE)
        return "".join(
            segment
            if segment.lower().startswith("<a")
            else apply_basic_inline_styles(segment)
            for segment in segments
        )

    html = LINK_PATTERN.sub(replace_link, escaped_text)
    html = WIKI_LINK_PATTERN.sub(replace_wiki_link, html)
    html = auto_link_text_segments(html)
    return style_text_segments(html)


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


def parse_chronos_dates(value: str) -> tuple[str, str | None]:
    if "~" not in value:
        return value.strip(), None

    start, end = value.split("~", 1)
    return start.strip(), end.strip() or None


def parse_chronos_modifiers(text: str) -> tuple[str | None, str | None, str]:
    color = None
    group = None
    rest = text.strip()

    while rest:
        color_match = CHRONOS_COLOR_PATTERN.match(rest)
        if color_match:
            candidate = color_match.group(1).lower()
            if candidate in CHRONOS_COLORS or re.fullmatch(r"[0-9a-f]{3,8}", candidate):
                color = candidate
                rest = rest[color_match.end() :].strip()
                continue

        group_match = CHRONOS_GROUP_PATTERN.match(rest)
        if group_match:
            group = group_match.group(1).strip()
            rest = rest[group_match.end() :].strip()
            continue

        break

    return color, group, rest


def parse_chronos_item(line: str) -> dict[str, str | None] | None:
    match = CHRONOS_ITEM_PATTERN.match(line)
    if not match:
        return None

    symbol = match.group(1)
    start, end = parse_chronos_dates(match.group(2))
    color, group, content = parse_chronos_modifiers(match.group(3))
    title, _, description = content.partition("|")
    item_type = {
        "-": "event",
        "@": "period",
        "*": "point",
        "=": "marker",
        "~": "marker",
    }[symbol]

    if item_type == "point":
        end = None

    return {
        "type": item_type,
        "symbol": symbol,
        "start": start,
        "end": end,
        "color": color,
        "group": group,
        "content": title.strip(),
        "description": description.strip() or None,
        "raw": line,
    }


def parse_chronos_block(text: str) -> list[dict[str, str | None]]:
    items: list[dict[str, str | None]] = []

    for line in text.splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#") or stripped_line.startswith(">"):
            continue

        item = parse_chronos_item(stripped_line)
        if item is not None:
            items.append(item)

    return items


def render_chronos_block(text: str) -> str:
    payload = json.dumps(
        {"items": parse_chronos_block(text)},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    return (
        '<div class="chronos-block chronos-timeline-container">'
        '<div class="chronos-output" aria-label="Chronos timeline"></div>'
        '<script type="application/json" class="chronos-data">'
        f"{payload}"
        "</script>"
        '<noscript><pre class="chronos-source">'
        f"{escape(text)}"
        "</pre></noscript>"
        "</div>"
    )


def render_blockquote(
    quote_lines: list[str],
    wiki_link_index: dict[str, Path],
    current_target: Path,
) -> str:
    content = "<br>\n".join(
        transform_inline_markdown(line, wiki_link_index, current_target)
        for line in quote_lines
    )
    return f"<blockquote>\n<p>{content}</p>\n</blockquote>"


def render_callout(
    callout_type: str,
    title: str,
    body_lines: list[str],
    wiki_link_index: dict[str, Path],
    current_target: Path,
) -> str:
    display_title = title or callout_type.title()
    title_html = transform_inline_markdown(display_title, wiki_link_index, current_target)
    body_content = "<br>\n".join(
        transform_inline_markdown(line, wiki_link_index, current_target)
        for line in body_lines
    )
    body_html = (
        f'\n<div class="callout-content">\n<p>{body_content}</p>\n</div>'
        if body_lines
        else ""
    )
    return (
        f'<div class="callout callout-{callout_type}" data-callout="{callout_type}">\n'
        '<div class="callout-title"><span class="callout-icon" '
        f'aria-hidden="true"></span>{title_html}</div>'
        f"{body_html}\n"
        "</div>"
    )


def render_task_item(
    checked: bool,
    text: str,
    wiki_link_index: dict[str, Path],
    current_target: Path,
) -> str:
    checked_attribute = " checked" if checked else ""
    content = transform_inline_markdown(text, wiki_link_index, current_target)
    return (
        '<p class="task-list-item">'
        f'<input type="checkbox" disabled{checked_attribute}> '
        f"{content}</p>"
    )


def render_unordered_list(
    items: list[str],
    wiki_link_index: dict[str, Path],
    current_target: Path,
) -> str:
    list_items = "\n".join(
        f"<li>{transform_inline_markdown(item, wiki_link_index, current_target)}</li>"
        for item in items
    )
    return f"<ul>\n{list_items}\n</ul>"


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
    chronos_js_href: str,
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
                elif code_block_language == "chronos":
                    html_lines.append(render_chronos_block(code))
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

        if stripped_line == "---":
            html_lines.append("<hr>")
            index += 1
            continue

        task_match = TASK_ITEM_PATTERN.match(stripped_line)
        if task_match:
            html_lines.append(
                render_task_item(
                    task_match.group(1).lower() == "x",
                    task_match.group(2) or "",
                    wiki_link_index,
                    current_target,
                )
            )
            index += 1
            continue

        list_match = UNORDERED_LIST_ITEM_PATTERN.match(stripped_line)
        if list_match:
            list_items = [list_match.group(1)]
            index += 1

            while index < len(lines):
                next_line = lines[index].strip()
                next_match = UNORDERED_LIST_ITEM_PATTERN.match(next_line)
                if not next_match:
                    break
                list_items.append(next_match.group(1))
                index += 1

            html_lines.append(
                render_unordered_list(list_items, wiki_link_index, current_target)
            )
            continue

        if stripped_line.startswith(">"):
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_line = re.sub(r"^\s*>\s?", "", lines[index])
                quote_lines.append(quote_line)
                index += 1

            callout_match = (
                CALLOUT_PATTERN.match(quote_lines[0]) if quote_lines else None
            )
            if callout_match and callout_match.group(1).lower() in CALLOUT_TYPES:
                callout_type = callout_match.group(1).lower()
                html_lines.append(
                    render_callout(
                        callout_type,
                        callout_match.group(2).strip(),
                        quote_lines[1:],
                        wiki_link_index,
                        current_target,
                    )
                )
            else:
                html_lines.append(
                    render_blockquote(quote_lines, wiki_link_index, current_target)
                )
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
        elif code_block_language == "chronos":
            html_lines.append(render_chronos_block(code))
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
        f'  <script defer src="{chronos_js_href}"></script>\n'
        "</head>\n"
        "<body>\n"
        '<button type="button" class="mode-toggle" data-mode-toggle>dark</button>\n'
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )
