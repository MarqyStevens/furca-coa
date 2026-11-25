#!/usr/bin/env python3
import argparse
import base64
import math
import shutil
import struct
import sys
import zlib

GOLD_RGB = (253, 218, 42)
BLACK_RGB = (17, 17, 17)

# Polyline wedge segments inside the shield (x1, y1, x2, y2, slope)
WEDGE_SEGMENTS = (
    (0.0, 560.0, 83.0, 5.0, -555.0 / 83.0),
    (83.0, 5.0, 166.0, 560.0, 555.0 / 83.0),
    (166.0, 560.0, 250.0, 5.0, -555.0 / 84.0),
    (250.0, 5.0, 335.0, 560.0, 555.0 / 85.0),
    (335.0, 560.0, 417.0, 5.0, -555.0 / 82.0),
    (417.0, 5.0, 500.0, 560.0, 555.0 / 83.0),
)

# 2x2 Quadrant Unicode block elements indexed by bitmask:
# bit 0 (1)=top-left, bit 1 (2)=top-right, bit 2 (4)=bot-left, bit 3 (8)=bot-right
QUADRANT_CHARS = (
    " ", "▘", "▝", "▀",
    "▖", "▌", "▞", "▛",
    "▗", "▚", "▐", "▜",
    "▄", "▙", "▟", "█",
)


def _build_sextant_chars():
    """Build 64-entry lookup table for 2x3 Unicode sextant glyphs (U+1FB00..U+1FB3B)."""
    chars = []
    cp = 0x1FB00
    for mask in range(64):
        if mask == 0:
            chars.append(" ")
        elif mask == 21:  # bits 0, 2, 4 -> left half block
            chars.append("▌")
        elif mask == 42:  # bits 1, 3, 5 -> right half block
            chars.append("▐")
        elif mask == 63:
            chars.append("█")
        else:
            chars.append(chr(cp))
            cp += 1
    return tuple(chars)


SEXTANT_CHARS = _build_sextant_chars()


def get_color(x, y, draw_border=True):
    """Return 'B', 'G', or None at SVG coordinate (x, y) in [0, 500] x [0, 580]."""
    if x < 0.0 or x > 500.0 or y < 0.0 or y > 580.0:
        return None

    if y > 330.0:
        dx_c = x - 250.0
        dy_c = y - 330.0
        r2 = dx_c * dx_c + dy_c * dy_c
        if r2 > 62500.0:  # 250^2 (outer shield field)
            return None
        if draw_border and r2 >= 59536.0:  # 244^2 (inner edge of 6px stroke)
            return "B"
        if not draw_border and r2 > 61009.0:  # 247^2 (clip-path boundary)
            return "G"
    else:
        if draw_border and (y <= 6.0 or x <= 6.0 or x >= 494.0):
            return "B"
        if not draw_border and (y < 3.0 or x < 3.0 or x > 497.0):
            return "G"

    if x < 83.0:
        y_boundary = 560.0 - (555.0 / 83.0) * x
    elif x < 166.0:
        y_boundary = 5.0 + (555.0 / 83.0) * (x - 83.0)
    elif x < 250.0:
        y_boundary = 560.0 - (555.0 / 84.0) * (x - 166.0)
    elif x < 335.0:
        y_boundary = 5.0 + (555.0 / 85.0) * (x - 250.0)
    elif x < 417.0:
        y_boundary = 560.0 - (555.0 / 82.0) * (x - 335.0)
    else:
        y_boundary = 5.0 + (555.0 / 83.0) * (x - 417.0)

    return "B" if y >= y_boundary else "G"


def _is_edge_pixel(x, y, hx, hy, draw_border):
    """Conservative check whether the rectangle [x-hx, x+hx] x [y-hy, y+hy] crosses an edge."""
    if x + hx >= 0.0 and x - hx <= 500.0 and y + hy >= 0.0 and y - hy <= 580.0:
        margin = max(hx, hy)
        if y - hy <= 6.0 or x - hx <= 6.0 or x + hx >= 494.0:
            return True
        if y + hy >= 330.0:
            r = math.hypot(x - 250.0, max(0.0, y - 330.0))
            inner_r = 244.0 if draw_border else 247.0
            if (inner_r - margin * 1.42) <= r <= (250.0 + margin * 1.42):
                return True
        for x1, y1, x2, _y2, slope in WEDGE_SEGMENTS:
            if x + hx >= x1 and x - hx <= x2:
                x_lo = max(x - hx, x1)
                x_hi = min(x + hx, x2)
                y_lo = y1 + slope * (x_lo - x1)
                y_hi = y1 + slope * (x_hi - x1)
                if y_lo > y_hi:
                    y_lo, y_hi = y_hi, y_lo
                if y_hi >= y - hy and y_lo <= y + hy:
                    return True
    return False


def sample_pixel_rgba(x, y, dx, dy, draw_border=True, ss=4):
    """Return premultiplied-averaged straight RGBA tuple (r, g, b, a) for pixel centered at (x, y)."""
    hx = dx * 0.5
    hy = dy * 0.5
    if ss <= 1 or not _is_edge_pixel(x, y, hx, hy, draw_border):
        val = get_color(x, y, draw_border)
        if val is None:
            return (0, 0, 0, 0)
        rgb = GOLD_RGB if val == "G" else BLACK_RGB
        return (rgb[0], rgb[1], rgb[2], 255)

    n = ss * ss
    step_x = dx / ss
    step_y = dy / ss
    x0 = x - hx + step_x * 0.5
    y0 = y - hy + step_y * 0.5

    count_g = 0
    count_b = 0
    for sy in range(ss):
        py = y0 + sy * step_y
        for sx in range(ss):
            px = x0 + sx * step_x
            val = get_color(px, py, draw_border)
            if val == "G":
                count_g += 1
            elif val == "B":
                count_b += 1

    opaque = count_g + count_b
    if opaque == 0:
        return (0, 0, 0, 0)

    r = (count_g * GOLD_RGB[0] + count_b * BLACK_RGB[0] + opaque // 2) // opaque
    g = (count_g * GOLD_RGB[1] + count_b * BLACK_RGB[1] + opaque // 2) // opaque
    b = (count_g * GOLD_RGB[2] + count_b * BLACK_RGB[2] + opaque // 2) // opaque
    a = (opaque * 255 + n // 2) // n
    return (r, g, b, a)


def sample_pixel_term_rgb(x, y, dx, dy, draw_border=True, ss=4, bg_rgb=None):
    """Return (r, g, b) tuple or None for transparent background in TrueColor terminal mode."""
    hx = dx * 0.5
    hy = dy * 0.5
    if ss <= 1 or not _is_edge_pixel(x, y, hx, hy, draw_border):
        val = get_color(x, y, draw_border)
        if val is None:
            return bg_rgb
        return GOLD_RGB if val == "G" else BLACK_RGB

    n = ss * ss
    step_x = dx / ss
    step_y = dy / ss
    x0 = x - hx + step_x * 0.5
    y0 = y - hy + step_y * 0.5

    count_g = 0
    count_b = 0
    for sy in range(ss):
        py = y0 + sy * step_y
        for sx in range(ss):
            px = x0 + sx * step_x
            val = get_color(px, py, draw_border)
            if val == "G":
                count_g += 1
            elif val == "B":
                count_b += 1

    opaque = count_g + count_b
    if bg_rgb is not None:
        count_bg = n - opaque
        r = (count_g * GOLD_RGB[0] + count_b * BLACK_RGB[0] + count_bg * bg_rgb[0] + n // 2) // n
        g = (count_g * GOLD_RGB[1] + count_b * BLACK_RGB[1] + count_bg * bg_rgb[1] + n // 2) // n
        b = (count_g * GOLD_RGB[2] + count_b * BLACK_RGB[2] + count_bg * bg_rgb[2] + n // 2) // n
        return (r, g, b)

    if opaque * 2 < n:
        return None

    r = (count_g * GOLD_RGB[0] + count_b * BLACK_RGB[0] + opaque // 2) // opaque
    g = (count_g * GOLD_RGB[1] + count_b * BLACK_RGB[1] + opaque // 2) // opaque
    b = (count_g * GOLD_RGB[2] + count_b * BLACK_RGB[2] + opaque // 2) // opaque
    return (r, g, b)


def _palette_rgb(token):
    if token == "G":
        return GOLD_RGB
    if token == "B":
        return BLACK_RGB
    return token


def get_ansi_codes(fg, bg, mode):
    fg_code = ""
    bg_code = ""

    if mode == "truecolor":
        if fg is None:
            fg_code = "\x1b[39m"
        else:
            r, g, b = _palette_rgb(fg)
            fg_code = f"\x1b[38;2;{r};{g};{b}m"

        if bg is None:
            bg_code = "\x1b[49m"
        else:
            r, g, b = _palette_rgb(bg)
            bg_code = f"\x1b[48;2;{r};{g};{b}m"

    elif mode == "256":
        if fg == "G":
            fg_code = "\x1b[38;5;220m"
        elif fg == "B":
            fg_code = "\x1b[38;5;233m"
        else:
            fg_code = "\x1b[39m"

        if bg == "G":
            bg_code = "\x1b[48;5;220m"
        elif bg == "B":
            bg_code = "\x1b[48;5;233m"
        else:
            bg_code = "\x1b[49m"

    elif mode == "16":
        if fg == "G":
            fg_code = "\x1b[33m"
        elif fg == "B":
            fg_code = "\x1b[30m"
        else:
            fg_code = "\x1b[39m"

        if bg == "G":
            bg_code = "\x1b[43m"
        elif bg == "B":
            bg_code = "\x1b[40m"
        else:
            bg_code = "\x1b[49m"

    return fg_code + bg_code


def _emit_cell(row_chars, fg, bg, char, last_fg, last_bg, mode):
    if fg != last_fg or bg != last_bg:
        row_chars.append(get_ansi_codes(fg, bg, mode) + char)
        return fg, bg
    row_chars.append(char)
    return last_fg, last_bg


def render_half_block(width, height, mode, draw_border=True, ss=4, bg_rgb=None):
    lines = []
    dx = 500.0 / width
    dy = 580.0 / (2.0 * height)
    use_aa = mode == "truecolor" and (ss > 1 or bg_rgb is not None)

    for row in range(height):
        row_chars = []
        last_fg = None
        last_bg = None
        y_top = (2 * row) * dy + dy * 0.5
        y_bottom = (2 * row + 1) * dy + dy * 0.5

        for col in range(width):
            x = col * dx + dx * 0.5

            if use_aa:
                top_val = sample_pixel_term_rgb(x, y_top, dx, dy, draw_border, ss, bg_rgb)
                bot_val = sample_pixel_term_rgb(x, y_bottom, dx, dy, draw_border, ss, bg_rgb)
            else:
                top_val = get_color(x, y_top, draw_border)
                bot_val = get_color(x, y_bottom, draw_border)

            if mode == "ascii":
                char = " "
                if top_val == "G" and bot_val == "G":
                    char = "#"
                elif top_val == "B" and bot_val == "B":
                    char = "."
                elif top_val == "G" and bot_val == "B":
                    char = "^"
                elif top_val == "B" and bot_val == "G":
                    char = "v"
                elif top_val == "G":
                    char = "'"
                elif bot_val == "G":
                    char = ","
                elif top_val == "B":
                    char = "`"
                elif bot_val == "B":
                    char = "."
                row_chars.append(char)
            else:
                if top_val is None and bot_val is None:
                    fg, bg, char = None, None, " "
                elif top_val == bot_val:
                    fg, bg, char = top_val, None, "█"
                elif top_val is not None and bot_val is not None:
                    fg, bg, char = top_val, bot_val, "▀"
                elif top_val is not None:
                    fg, bg, char = top_val, None, "▀"
                else:
                    fg, bg, char = bot_val, None, "▄"

                last_fg, last_bg = _emit_cell(row_chars, fg, bg, char, last_fg, last_bg, mode)

        row_str = "".join(row_chars)
        if mode != "ascii":
            row_str += "\x1b[0m"
        lines.append(row_str)
    return "\n".join(lines)


def render_standard_block(width, height, mode, draw_border=True, ss=4, bg_rgb=None):
    lines = []
    dx = 500.0 / width
    dy = 580.0 / height
    use_aa = mode == "truecolor" and (ss > 1 or bg_rgb is not None)

    for row in range(height):
        row_chars = []
        last_fg = None
        last_bg = None
        y = row * dy + dy * 0.5

        for col in range(width):
            x = col * dx + dx * 0.5

            if use_aa:
                val = sample_pixel_term_rgb(x, y, dx, dy, draw_border, ss, bg_rgb)
            else:
                val = get_color(x, y, draw_border)

            if mode == "ascii":
                char = " "
                if val == "G":
                    char = "#"
                elif val == "B":
                    char = "."
                row_chars.append(char)
            else:
                if val is None:
                    fg, bg, char = None, None, " "
                else:
                    fg, bg, char = val, None, "█"
                last_fg, last_bg = _emit_cell(row_chars, fg, bg, char, last_fg, last_bg, mode)

        row_str = "".join(row_chars)
        if mode != "ascii":
            row_str += "\x1b[0m"
        lines.append(row_str)
    return "\n".join(lines)


def _encode_subcell_2colors(vals, full_mask):
    """Map N subpixel tokens (None/'G'/'B') into (fg, bg, bitmask) for 2-color cell glyphs."""
    first = vals[0]
    if all(v == first for v in vals):
        if first is None:
            return None, None, 0
        return first, None, full_mask

    has_none = None in vals
    has_g = "G" in vals
    has_b = "B" in vals

    if has_none:
        bg = None
        if has_b and has_g:
            fg = "B"
            mask = 0
            for idx, v in enumerate(vals):
                if v is not None:
                    mask |= 1 << idx
            return fg, bg, mask
        fg = "B" if has_b else "G"
        mask = 0
        for idx, v in enumerate(vals):
            if v == fg:
                mask |= 1 << idx
        return fg, bg, mask

    fg = "B"
    bg = "G"
    mask = 0
    for idx, v in enumerate(vals):
        if v == "B":
            mask |= 1 << idx
    return fg, bg, mask


def render_subcell_grid(width, height, sub_w, sub_h, char_table, mode, draw_border=True):
    """Render 2x2 (quadrant) or 2x3 (sextant) sub-character block graphics."""
    lines = []
    dx = 500.0 / (width * sub_w)
    dy = 580.0 / (height * sub_h)
    full_mask = (1 << (sub_w * sub_h)) - 1

    for row in range(height):
        row_chars = []
        last_fg = None
        last_bg = None
        ys = [(row * sub_h + sy) * dy + dy * 0.5 for sy in range(sub_h)]

        for col in range(width):
            xs = [(col * sub_w + sx) * dx + dx * 0.5 for sx in range(sub_w)]
            vals = [get_color(px, py, draw_border) for py in ys for px in xs]
            fg, bg, mask = _encode_subcell_2colors(vals, full_mask)
            char = char_table[mask]
            last_fg, last_bg = _emit_cell(row_chars, fg, bg, char, last_fg, last_bg, mode)

        lines.append("".join(row_chars) + "\x1b[0m")
    return "\n".join(lines)


def rasterize_rgba(pixel_w, pixel_h, draw_border=True, ss=4):
    """Rasterize the coat of arms into raw RGBA rows (list of bytes objects)."""
    dx = 500.0 / pixel_w
    dy = 580.0 / pixel_h
    rows = []
    for py in range(pixel_h):
        y = py * dy + dy * 0.5
        row = bytearray(pixel_w * 4)
        offset = 0
        for px in range(pixel_w):
            x = px * dx + dx * 0.5
            r, g, b, a = sample_pixel_rgba(x, y, dx, dy, draw_border, ss)
            row[offset] = r
            row[offset + 1] = g
            row[offset + 2] = b
            row[offset + 3] = a
            offset += 4
        rows.append(bytes(row))
    return rows


def encode_png(pixel_w, pixel_h, rgba_rows):
    """Encode RGBA rows into a PNG byte string using Python stdlib only."""
    def _chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    for row in rgba_rows:
        raw.append(0)  # Filter type 0 (None)
        raw.extend(row)

    ihdr = struct.pack(">IIBBBBB", pixel_w, pixel_h, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), level=6)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def format_kitty_graphics(png_bytes, cols=None, rows=None):
    """Format PNG bytes as Kitty Graphics Protocol escape sequence."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    chunk_size = 4096
    chunks = [b64[i:i + chunk_size] for i in range(0, len(b64), chunk_size)]
    size_params = ""
    if cols and rows:
        size_params = f",c={cols},r={rows}"

    out = []
    for idx, chunk in enumerate(chunks):
        more = 1 if idx < len(chunks) - 1 else 0
        if idx == 0:
            out.append(f"\x1b_Ga=T,f=100,q=2{size_params},m={more};{chunk}\x1b\\")
        else:
            out.append(f"\x1b_Gm={more};{chunk}\x1b\\")
    return "".join(out)


def format_iterm2_image(png_bytes, cols=None, rows=None):
    """Format PNG bytes as iTerm2 Inline Images Protocol escape sequence."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    dims = ""
    if cols and rows:
        dims = f";width={cols};height={rows}"
    return f"\x1b]1337;File=inline=1;size={len(png_bytes)}{dims};preserveAspectRatio=1:{b64}\x07"


def format_sixel(pixel_w, pixel_h, rgba_rows):
    """Format RGBA rows into a 17-shade anti-aliased Sixel graphics sequence."""
    n_shades = 17  # 0 = black (#111111), 16 = gold (#FDDA2A)
    out = [f'\x1bP0;1;0q"1;1;{pixel_w};{pixel_h}']

    for idx in range(n_shades):
        t = idx / (n_shades - 1)
        r = round((BLACK_RGB[0] + t * (GOLD_RGB[0] - BLACK_RGB[0])) * 100.0 / 255.0)
        g = round((BLACK_RGB[1] + t * (GOLD_RGB[1] - BLACK_RGB[1])) * 100.0 / 255.0)
        b = round((BLACK_RGB[2] + t * (GOLD_RGB[2] - BLACK_RGB[2])) * 100.0 / 255.0)
        out.append(f"#{idx};2;{r};{g};{b}")

    gold_span = GOLD_RGB[0] - BLACK_RGB[0]
    for y0 in range(0, pixel_h, 6):
        band_h = min(6, pixel_h - y0)
        per_color = {}
        for bit in range(band_h):
            row = rgba_rows[y0 + bit]
            bit_val = 1 << bit
            for px in range(pixel_w):
                off = px * 4
                if row[off + 3] < 128:
                    continue
                r = row[off]
                t = max(0.0, min(1.0, (r - BLACK_RGB[0]) / gold_span))
                c_idx = round(t * (n_shades - 1))
                buf = per_color.get(c_idx)
                if buf is None:
                    buf = [0] * pixel_w
                    per_color[c_idx] = buf
                buf[px] |= bit_val

        if not per_color:
            out.append("-")
            continue

        first_color = True
        for c_idx in sorted(per_color):
            buf = per_color[c_idx]
            if not first_color:
                out.append("$")
            first_color = False
            out.append(f"#{c_idx}")

            i = 0
            while i < pixel_w:
                val = buf[i]
                j = i + 1
                while j < pixel_w and buf[j] == val:
                    j += 1
                run_len = j - i
                ch = chr(63 + val)
                if run_len >= 4:
                    out.append(f"!{run_len}{ch}")
                else:
                    out.append(ch * run_len)
                i = j
        out.append("-")

    out.append("\x1b\\")
    return "".join(out)


def parse_hex_color(value):
    s = value.strip().lstrip("#")
    if len(s) != 6:
        raise argparse.ArgumentTypeError(f"Expected 6-digit hex color like #1e1e2e, got {value!r}")
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid hex color {value!r}") from exc


def get_default_dimensions():
    try:
        columns, lines = shutil.get_terminal_size((80, 24))
    except Exception:
        columns, lines = 80, 24

    usable_lines = max(8, lines - 6)
    max_w_chars = int(columns * 0.9)

    # Physical terminal cell ratio is ~1:2 (width:height).
    # So width_cols / (2 * height_rows) = 500 / 580.
    w_chars = int(round(usable_lines * 2.0 * (500.0 / 580.0)))
    h_chars = usable_lines

    if w_chars > max_w_chars:
        w_chars = max_w_chars
        h_chars = int(round((w_chars / 2.0) * (580.0 / 500.0)))

    return max(4, w_chars), max(4, h_chars)


def print_info(mode):
    yellow_ansi = "\x1b[33m" if mode != "ascii" else ""
    bold_ansi = "\x1b[1m" if mode != "ascii" else ""
    reset_ansi = "\x1b[0m" if mode != "ascii" else ""

    info_text = f"""
{bold_ansi}{yellow_ansi}══════════════════════════════════════════════════════════════════════════
               COAT OF ARMS OF DARGOVSKÝCH HRDINOV (FURČA)
══════════════════════════════════════════════════════════════════════════{reset_ansi}

{bold_ansi}Official Description (Blazón):{reset_ansi}
  "V zlatom štíte tri čierne kliny" 
  (In a golden shield, three black wedges/piles).

{bold_ansi}Symbolism:{reset_ansi}
  The three black wedges are a stylized, geometric representation of the
  "úvrate" (ravines, turns, or steep slopes) that cut into the hill upon
  which the borough of Dargovských hrdinov is built.

{bold_ansi}History & Name Origins:{reset_ansi}
  • {bold_ansi}Official Name:{reset_ansi} Dargovských hrdinov (Dargov Heroes) honors the veterans
    of the Battle of Dargov Pass in the Slanské Hills (January 1945), a major 
    World War II conflict where the Red Army broke through German defense lines.
  • {bold_ansi}The Nickname "Furča":{reset_ansi} In everyday language, locals almost exclusively use 
    the historic name "Furča". There are two primary theories for this name:
      1. {bold_ansi}Latin Origin (Historical):{reset_ansi} Derived from the Latin "furca" (or "furcilla" 
         meaning fork/vidlica). The forest atop the hill, as viewed from old 
         Košice, had a distinct fork-like shape. Similar names (Fourche, Furche)
         were common in areas of Germany from which medieval settlers arrived.
      2. {bold_ansi}Hungarian Origin (Folk Legend):{reset_ansi} Derived from "furcsa" 
         meaning "strange" or "weird", reflecting old tales of bizarre events 
         and merchant ambushes in the deep forests on the hill.

{bold_ansi}Adoption:{reset_ansi}
  The coat of arms and flag were designed by JUDr. Jozef Kirst. They were adopted
  by the local council on December 17, 2007, and registered in the Heraldic
  Register of the Slovak Republic under the signature D-173/2008.
══════════════════════════════════════════════════════════════════════════
"""
    print(info_text)


def main():
    parser = argparse.ArgumentParser(
        description="Render a terminal graphic or high-res PNG of the Coat of Arms of Furča (Košice-Dargovských hrdinov)."
    )
    parser.add_argument("--width", type=int, help="Width of the graphic in character columns.")
    parser.add_argument("--height", type=int, help="Height of the graphic in character rows.")
    parser.add_argument(
        "--color-mode",
        choices=["truecolor", "256", "16", "ascii"],
        default="truecolor",
        help="Color mode for text render modes. 'truecolor' (24-bit RGB), '256' (8-bit ANSI), '16' (basic ANSI), or 'ascii' (text art).",
    )
    parser.add_argument(
        "--render-mode",
        choices=["half", "quadrant", "sextant", "standard", "kitty", "iterm2", "sixel"],
        default="half",
        help=(
            "Render resolution mode: 'half' (1x2 px/cell, default), 'quadrant' (2x2 px/cell), "
            "'sextant' (2x3 px/cell, Unicode 13), 'standard' (1x1 px/cell), or native pixel protocols "
            "'kitty', 'iterm2', 'sixel'."
        ),
    )
    parser.add_argument(
        "--aa",
        type=int,
        default=4,
        help="Supersampling factor (NxN) for anti-aliasing in truecolor/pixel modes (default: 4, set 1 to disable).",
    )
    parser.add_argument(
        "--bg",
        type=parse_hex_color,
        default=None,
        help="Optional terminal background hex color (e.g. #000000) for anti-aliasing the outer shield border in truecolor modes.",
    )
    parser.add_argument(
        "--pixel-width",
        type=int,
        help="Raster width in pixels for 'kitty', 'iterm2', 'sixel', or --save-png (default: 1000, or 500 for sixel).",
    )
    parser.add_argument(
        "--pixel-height",
        type=int,
        help="Raster height in pixels (auto-calculated from 500:580 aspect ratio if omitted).",
    )
    parser.add_argument(
        "--save-png",
        metavar="PATH",
        help="Write an anti-aliased transparent RGBA PNG file to PATH.",
    )
    parser.add_argument("--no-border", action="store_true", help="Do not draw the black shield border.")
    parser.add_argument("--info", action="store_true", help="Print historical and symbolic information about the coat of arms.")

    args = parser.parse_args()

    if args.aa < 1:
        parser.error("--aa must be >= 1")
    if args.color_mode == "ascii" and args.render_mode in ("quadrant", "sextant"):
        parser.error(f"--render-mode {args.render_mode} requires color output (cannot be used with --color-mode ascii)")

    draw_border = not args.no_border

    if args.save_png:
        px_w = args.pixel_width or 1000
        px_h = args.pixel_height or int(round(px_w * (580.0 / 500.0)))
        rgba_rows = rasterize_rgba(px_w, px_h, draw_border=draw_border, ss=args.aa)
        png_bytes = encode_png(px_w, px_h, rgba_rows)
        with open(args.save_png, "wb") as f:
            f.write(png_bytes)
        print(f"Saved {px_w}x{px_h} PNG to {args.save_png}")
        if not args.info and args.render_mode == "half" and args.width is None and args.height is None:
            return

    if args.info:
        print_info(args.color_mode)

    if args.width and args.height:
        width, height = args.width, args.height
    elif args.width:
        width = args.width
        height = int(round((width / 2.0) * (580.0 / 500.0)))
    elif args.height:
        height = args.height
        width = int(round(height * 2.0 * (500.0 / 580.0)))
    else:
        width, height = get_default_dimensions()

    bold_ansi = "\x1b[1m" if args.color_mode != "ascii" else ""
    reset_ansi = "\x1b[0m" if args.color_mode != "ascii" else ""

    print(f"\n{bold_ansi}         Coat of Arms of Furča (Košice-Dargovských hrdinov){reset_ansi}\n")

    if args.render_mode in ("kitty", "iterm2", "sixel"):
        default_pw = 500 if args.render_mode == "sixel" else 1000
        px_w = args.pixel_width or default_pw
        px_h = args.pixel_height or int(round(px_w * (580.0 / 500.0)))
        rgba_rows = rasterize_rgba(px_w, px_h, draw_border=draw_border, ss=args.aa)

        if args.render_mode == "kitty":
            png_bytes = encode_png(px_w, px_h, rgba_rows)
            graphic = format_kitty_graphics(png_bytes, cols=width, rows=height)
        elif args.render_mode == "iterm2":
            png_bytes = encode_png(px_w, px_h, rgba_rows)
            graphic = format_iterm2_image(png_bytes, cols=width, rows=height)
        else:
            graphic = format_sixel(px_w, px_h, rgba_rows)
        sys.stdout.write(graphic + "\n\n")
        sys.stdout.flush()
        return

    if args.render_mode == "half":
        graphic = render_half_block(width, height, args.color_mode, draw_border, ss=args.aa, bg_rgb=args.bg)
    elif args.render_mode == "quadrant":
        graphic = render_subcell_grid(width, height, 2, 2, QUADRANT_CHARS, args.color_mode, draw_border)
    elif args.render_mode == "sextant":
        graphic = render_subcell_grid(width, height, 2, 3, SEXTANT_CHARS, args.color_mode, draw_border)
    else:
        graphic = render_standard_block(width, height, args.color_mode, draw_border, ss=args.aa, bg_rgb=args.bg)

    print(graphic)
    print()


if __name__ == "__main__":
    main()
