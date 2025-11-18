"""
YAML snippet import utilities for the reTerminal Dashboard Designer integration.

This module provides a BEST-EFFORT, SAFE parser that can reconstruct the internal
layout model (DeviceConfig/PageConfig/WidgetConfig) from an ESPHome YAML snippet.

Goals:
- Allow advanced users to:
  - Start from the visual editor.
  - Tweak the generated YAML snippet by hand.
  - Import that snippet back into the editor for further refinement.
- Support "any YAML that roughly follows our snippet pattern":
  - Known `display_page` global.
  - A `display` lambda using `int page = id(display_page);` and `if (page == N) { ... }`.
  - Widget draw calls emitted in a predictable format.

Non-goals:
- Parsing arbitrary, free-form ESPHome configurations.
- Guessing layouts from unrelated code.

Behavior:
- Only parses structures it recognizes.
- If it cannot parse safely, it raises a ValueError with a clear code:
  - "invalid_yaml"
  - "unrecognized_display_structure"
  - "no_pages_found"
- The caller (HTTP API) should return a clear error response to the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import yaml

from .models import DeviceConfig, PageConfig, WidgetConfig


# Add custom constructor for ESPHome YAML tags like !lambda, !secret, etc.
def _esphome_tag_constructor(loader, tag_suffix, node):
    """Handle ESPHome custom tags by returning the value as-is."""
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    elif isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None


# Register multi-constructor for all ESPHome tags
yaml.SafeLoader.add_multi_constructor('!', _esphome_tag_constructor)


@dataclass
class ParsedWidget:
    """Intermediate structure extracted from lambda lines."""
    # Required fields (no defaults)
    id: str
    type: str
    x: int
    y: int
    width: int
    height: int
    # Optional fields (with defaults)
    title: str | None = None
    entity_id: str | None = None
    text: str | None = None
    code: str | None = None
    url: str | None = None
    path: str | None = None
    format: str | None = None
    invert: bool = False
    # Text widget properties
    font_family: str | None = None
    font_size: int | None = None
    font_style: str | None = None
    # Sensor text properties
    label_font_size: int | None = None
    value_font_size: int | None = None
    value_format: str | None = None
    # Common properties
    color: str | None = None
    # Shape properties
    fill: bool | None = None
    opacity: int | None = None
    border_width: int | None = None
    stroke_width: int | None = None
    # Icon/Battery properties
    size: int | None = None
    # Progress bar properties
    bar_height: int | None = None
    show_label: bool | None = None
    show_percentage: bool | None = None
    # Datetime properties
    time_font_size: int | None = None
    date_font_size: int | None = None


def yaml_to_layout(snippet: str) -> DeviceConfig:
    """
    Parse a snippet of ESPHome YAML and reconstruct a DeviceConfig.

    Expected pattern:
    - globals: display_page (optional but recommended)
    - display:
        - platform: waveshare_epaper (or similar)
        - id: epaper_display
        - lambda: |-
            int page = id(display_page);
            if (page == 0) { ... }
            if (page == 1) { ... }

    Inside each page block we look for lines in one of our known forms, for example:
    - // widget:label id:w_xxx
      it.printf(x, y, id(font_normal), "Text");
    - // widget:sensor id:w_xxx ent:sensor.entity_id
      it.printf(x, y, id(font_small), "Label: %s", id(some_id).state.c_str());

    If the snippet deviates too far from this pattern, we fail clearly.
    """
    try:
        data = yaml.safe_load(snippet) or {}
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid_yaml") from exc

    display_block = _find_display_block(data)
    if not display_block:
        raise ValueError("unrecognized_display_structure")

    lambda_src = display_block.get("lambda")
    if not isinstance(lambda_src, str):
        raise ValueError("unrecognized_display_structure")

    # Normalize lambda lines
    lambda_lines = [line.rstrip("\n") for line in lambda_src.split("\n")]
    pages = _parse_pages_from_lambda(lambda_lines)

    # Allow empty pages - we found page blocks even if they have no widgets
    # But if we found NO page blocks at all, that's an error
    if pages is None:
        raise ValueError("no_pages_found")

    device = DeviceConfig(
        device_id="reterminal_e1001",
        api_token="",
        name="reTerminal E1001",
        pages=[],
        current_page=0,
    )

    for page_index, widgets in sorted(pages.items(), key=lambda x: x[0]):
        page = PageConfig(
            id=f"page_{page_index}",
            name=f"Page {page_index + 1}",
            widgets=[],
        )
        for pw in widgets:
            # Build props based on widget type
            props = {}
            
            # Common properties from markers
            if pw.text:
                props["text"] = pw.text
            if pw.font_family:
                props["font_family"] = pw.font_family
            if pw.font_size is not None:
                props["font_size"] = pw.font_size
            if pw.font_style:
                props["font_style"] = pw.font_style
            if pw.color:
                props["color"] = pw.color
            if pw.opacity is not None:
                props["opacity"] = pw.opacity
                
            # Type-specific properties
            if pw.type in ("text", "label"):
                if pw.font_size is None:
                    props["font_size"] = 16
                if not pw.color:
                    props["color"] = "black"
                    
            elif pw.code:
                props["code"] = pw.code
                props["font_ref"] = "font_mdi_medium"
                props["fit_icon_to_frame"] = True
                props["size"] = pw.size or 40
                if not pw.color:
                    props["color"] = "black"
                    
            elif pw.type == "sensor_text":
                props["label_font_size"] = pw.label_font_size or 14
                props["value_font_size"] = pw.value_font_size or 20
                props["value_format"] = pw.value_format or "label_value"
                if not pw.color:
                    props["color"] = "black"
                    
            elif pw.type == "datetime":
                props["format"] = pw.format or "time_date"
                props["time_font_size"] = pw.time_font_size or 28
                props["date_font_size"] = pw.date_font_size or 16
                if not pw.color:
                    props["color"] = "black"
                    
            elif pw.type == "progress_bar":
                props["bar_height"] = pw.bar_height or 20
                props["show_percentage"] = pw.show_percentage if pw.show_percentage is not None else True
                props["show_label"] = pw.show_label if pw.show_label is not None else True
                if not pw.color:
                    props["color"] = "black"
                    
            elif pw.type == "battery_icon":
                props["size"] = pw.size or 40
                if not pw.color:
                    props["color"] = "black"
                    
            elif pw.type in ("shape_rect", "shape_circle"):
                props["fill"] = pw.fill if pw.fill is not None else False
                props["border_width"] = pw.border_width if pw.border_width is not None else 1
                props["opacity"] = pw.opacity if pw.opacity is not None else 100
                if not pw.color:
                    props["color"] = "black"
                    
            elif pw.type == "line":
                props["stroke_width"] = pw.stroke_width or 1
                if not pw.color:
                    props["color"] = "black"
                    
            elif pw.type == "image":
                props["path"] = pw.path or ""
                props["invert"] = pw.invert
                
            elif pw.type == "online_image":
                props["url"] = pw.url or ""
                props["interval_s"] = 300
            
            wc = WidgetConfig(
                id=pw.id,
                type=pw.type,
                x=pw.x,
                y=pw.y,
                width=pw.width,
                height=pw.height,
                entity_id=pw.entity_id,
                title=pw.title,
                icon=None,
                props=props,
            )
            # Log parsed coordinates for debugging
            _LOGGER.debug(f"Parsed widget {pw.id} type={pw.type} x={pw.x} y={pw.y} w={pw.width} h={pw.height}")
            wc.clamp_to_canvas()
            page.widgets.append(wc)
        device.pages.append(page)

    device.ensure_pages()
    return device


def _find_display_block(data: Any) -> Dict[str, Any] | None:
    """
    Locate the 'display:' block with an epaper_display and lambda.
    We accept both:
    - display:
        - platform: waveshare_epaper
          id: epaper_display
          lambda: |-
            ...
    """
    if not isinstance(data, dict):
        return None

    display = data.get("display")
    if isinstance(display, list):
        for block in display:
            if not isinstance(block, dict):
                continue
            if "lambda" in block and block.get("id") == "epaper_display":
                return block
    elif isinstance(display, dict):
        if "lambda" in display and display.get("id") == "epaper_display":
            return display

    return None


def _parse_pages_from_lambda(lines: List[str]) -> Dict[int, List[ParsedWidget]]:
    """
    Extract pages and widgets from the lambda body.

    Strategy:
    - Find 'int page = id(display_page);'
    - For each 'if (page == N) {' block:
      - Collect lines until matching '}'
      - Inside, look for:
        - widget markers in comments, OR
        - recognizable it.printf patterns.
    - If markers are absent, we still try to parse simple patterns safely.

    We use conservative defaults for width/height when not encoded:
    - width: 200
    - height: 60
    """
    pages: Dict[int, List[ParsedWidget]] = {}
    current_page: int | None = None
    brace_depth = 0

    for raw_line in lines:
        line = raw_line.strip()

        # Track page blocks - handle both patterns:
        # 1) if (page == 0) {
        # 2) if (id(display_page) == 0) {
        page_match = None
        if line.startswith("if (page ==") and "{" in line:
            # Pattern 1: if (page == 0) {
            try:
                num_str = line.split("==")[1].split(")")[0].strip()
                page_match = int(num_str)
            except Exception:  # noqa: BLE001
                pass
        elif line.startswith("if (id(display_page)") and "==" in line and "{" in line:
            # Pattern 2: if (id(display_page) == 0) {
            try:
                num_str = line.split("==")[1].split(")")[0].strip()
                page_match = int(num_str)
            except Exception:  # noqa: BLE001
                pass
        
        if page_match is not None:
            current_page = page_match
            pages.setdefault(current_page, [])
            brace_depth = 1
            continue

        if current_page is not None:
            # Adjust brace depth to detect block end
            open_count = line.count("{")
            close_count = line.count("}")
            brace_depth += open_count - close_count
            if brace_depth <= 0:
                current_page = None
                brace_depth = 0
                continue

            # Inside page block: look for our widget hints or patterns
            pw = _parse_widget_line(line)
            if pw:
                pages[current_page].append(pw)

    return pages


def _parse_widget_line(line: str) -> ParsedWidget | None:
    """
    Parse a single line into a ParsedWidget when possible.

    Supported patterns (best-effort):

    1) Explicit marker comments (strongly recommended in generator):

       // widget:label id:w_x type:label x:10 y:20 w:200 h:40 text:Title
       // widget:sensor id:w_y type:sensor x:10 y:20 w:200 h:40 ent:sensor.entity

    2) Simple it.printf fallback (less precise):

       it.printf(10, 20, id(font_normal), "Text");

    If we cannot confidently parse, return None.
    """
    # Pattern 1: comment-based markers
    if line.startswith("// widget:"):
        # Example:
        # // widget:label id:w_x type:label x:10 y:20 w:200 h:40 text:Title
        # // widget:icon id:w_x type:icon x:10 y:20 w:60 h:60 code:F0595
        # // widget:sensor_text id:w_x type:sensor_text x:10 y:20 w:200 h:60 ent:sensor.entity title:"Label"
        parts = line.replace("//", "").strip().split()
        meta: Dict[str, str] = {}
        
        # Handle quoted values (e.g., title:"My Label")
        i = 1
        while i < len(parts):
            part = parts[i]
            if ":" in part:
                key, val = part.split(":", 1)
                key = key.strip()
                # Check if value is quoted and spans multiple parts
                if val.startswith('"'):
                    if val.endswith('"') and len(val) > 1:
                        # Complete quoted value in one part
                        meta[key] = val.strip('"')
                    else:
                        # Quote spans multiple parts
                        quote_parts = [val.lstrip('"')]
                        i += 1
                        while i < len(parts):
                            if parts[i].endswith('"'):
                                quote_parts.append(parts[i].rstrip('"'))
                                break
                            quote_parts.append(parts[i])
                            i += 1
                        meta[key] = " ".join(quote_parts)
                else:
                    meta[key] = val.strip()
            i += 1

        wtype = meta.get("type") or parts[0].split(":")[1]
        wid = meta.get("id", f"w_{abs(hash(line)) % 99999}")
        x = int(meta.get("x", "40"))
        y = int(meta.get("y", "40"))
        w = int(meta.get("w", "200"))
        h = int(meta.get("h", "60"))
        ent = meta.get("ent") or meta.get("entity")  # Support both ent: and entity:
        text = meta.get("text")
        code = meta.get("code")
        title = meta.get("title") or meta.get("label")  # Support both title: and label:
        url = meta.get("url")
        path = meta.get("path")
        format_val = meta.get("format")
        invert_val = meta.get("invert", "false").lower() in ("true", "1", "yes")
        
        # Extract all properties from markers
        font_family = meta.get("font_family")
        font_style = meta.get("font_style")
        color = meta.get("color")
        
        # Parse integer properties with fallback
        def parse_int(val: str | None) -> int | None:
            if val:
                try:
                    return int(val)
                except ValueError:
                    pass
            return None
        
        # Parse boolean properties
        def parse_bool(val: str | None) -> bool | None:
            if val is None:
                return None
            return val.lower() in ("true", "1", "yes")
        
        font_size = parse_int(meta.get("font_size"))
        label_font_size = parse_int(meta.get("label_font"))
        value_font_size = parse_int(meta.get("value_font"))
        size = parse_int(meta.get("size"))
        opacity = parse_int(meta.get("opacity"))
        border_width = parse_int(meta.get("border_width")) or parse_int(meta.get("border"))
        stroke_width = parse_int(meta.get("stroke_width")) or parse_int(meta.get("stroke"))
        bar_height = parse_int(meta.get("bar_height"))
        time_font_size = parse_int(meta.get("time_font"))
        date_font_size = parse_int(meta.get("date_font"))
        
        fill = parse_bool(meta.get("fill"))
        show_label = parse_bool(meta.get("show_label"))
        show_percentage = parse_bool(meta.get("show_percentage")) or parse_bool(meta.get("show_pct"))

        return ParsedWidget(
            id=wid,
            type=wtype,
            x=x,
            y=y,
            width=w,
            height=h,
            title=title or text or None,
            entity_id=ent or None,
            text=text or None,
            code=code or None,
            url=url or None,
            path=path or None,
            format=format_val or None,
            invert=invert_val,
            font_family=font_family,
            font_size=font_size,
            font_style=font_style,
            label_font_size=label_font_size,
            value_font_size=value_font_size,
            value_format=format_val or None,
            color=color,
            fill=fill,
            opacity=opacity,
            border_width=border_width,
            stroke_width=stroke_width,
            size=size,
            bar_height=bar_height,
            show_label=show_label,
            show_percentage=show_percentage,
            time_font_size=time_font_size,
            date_font_size=date_font_size,
        )

    # Pattern 2: simple printf (VERY conservative)
    if line.startswith("it.printf(") and ")" in line:
        # it.printf(x, y, id(font), "Text");
        try:
            args_str = line[len("it.printf(") :].split(")")[0]
            args = [a.strip() for a in args_str.split(",")]
            if len(args) >= 4:
                x = int(args[0])
                y = int(args[1])
                raw_text = args[3].strip()
                if raw_text.startswith('"') and raw_text.endswith('"'):
                    text = raw_text.strip('"')
                else:
                    text = None
                return ParsedWidget(
                    id=f"w_{abs(hash(line)) % 99999}",
                    type="label",
                    x=x,
                    y=y,
                    width=200,
                    height=40,
                    title=text or None,
                    text=text,
                )
        except Exception:  # noqa: BLE001
            return None

    return None