#!/usr/bin/env python3
import os
import sys
import shutil
import argparse

# Precompute Bezier curve for the shield bottom boundary
def precompute_bezier():
    # P0 = (3, 330), P1 = (3, 466.414), P2 = (113.586, 577), P3 = (250, 577)
    left_y_to_x = {}
    for i in range(10001):
        t = i / 10000.0
        x = (1-t)**3 * 3 + 3*(1-t)**2 * t * 3 + 3*(1-t) * t**2 * 113.586 + t**3 * 250
        y = (1-t)**3 * 330 + 3*(1-t)**2 * t * 466.414 + 3*(1-t) * t**2 * 577 + t**3 * 577
        
        y_int = int(round(y))
        if y_int not in left_y_to_x:
            left_y_to_x[y_int] = x
        else:
            left_y_to_x[y_int] = min(left_y_to_x[y_int], x)
            
    for y in range(330, 578):
        if y not in left_y_to_x:
            smaller = [k for k in left_y_to_x.keys() if k < y]
            larger = [k for k in left_y_to_x.keys() if k > y]
            if smaller and larger:
                s_y = max(smaller)
                l_y = min(larger)
                left_y_to_x[y] = left_y_to_x[s_y] + (left_y_to_x[l_y] - left_y_to_x[s_y]) * (y - s_y) / (l_y - s_y)
            elif smaller:
                left_y_to_x[y] = left_y_to_x[max(smaller)]
            elif larger:
                left_y_to_x[y] = left_y_to_x[min(larger)]
    return left_y_to_x

def get_color(x, y, left_y_to_x, draw_border=True):
    # Viewbox constraints
    if x < 3 or x > 497 or y < 3 or y > 577:
        return None
        
    # Check if inside shield
    if y <= 330:
        inside = True
        x_left = 3
    else:
        x_left = left_y_to_x.get(int(round(y)), 3.0)
        inside = (x_left <= x <= 500.0 - x_left)
        
    if not inside:
        return None
        
    # Check border (stroke-width = 6, so radius of 3 from boundary)
    if draw_border:
        if y <= 7:
            return 'B'
        if y <= 330:
            if x <= 7 or x >= 493:
                return 'B'
        else:
            if x <= x_left + 4 or x >= 500.0 - x_left - 4:
                return 'B'
            
    # Check polyline wedges (black region)
    # y_boundary(x)
    if 0 <= x < 83:
        y_boundary = 560 - (555 / 83.0) * x
    elif 83 <= x < 166:
        y_boundary = 5 + (555 / 83.0) * (x - 83.0)
    elif 166 <= x < 250:
        y_boundary = 560 - (555 / 84.0) * (x - 166.0)
    elif 250 <= x < 335:
        y_boundary = 5 + (555 / 85.0) * (x - 250.0)
    elif 335 <= x < 417:
        y_boundary = 560 - (555 / 82.0) * (x - 335.0)
    else: # 417 <= x <= 500
        y_boundary = 5 + (555 / 83.0) * (x - 417.0)
        
    if y >= y_boundary:
        return 'B'
    else:
        return 'G'

def get_ansi_codes(fg, bg, mode):
    fg_code = ""
    bg_code = ""
    
    if mode == 'truecolor':
        if fg == 'G':
            fg_code = "\x1b[38;2;253;218;42m"
        elif fg == 'B':
            fg_code = "\x1b[38;2;17;17;17m"
        else:
            fg_code = "\x1b[39m"
            
        if bg == 'G':
            bg_code = "\x1b[48;2;253;218;42m"
        elif bg == 'B':
            bg_code = "\x1b[48;2;17;17;17m"
        else:
            bg_code = "\x1b[49m"
            
    elif mode == '256':
        if fg == 'G':
            fg_code = "\x1b[38;5;220m"
        elif fg == 'B':
            fg_code = "\x1b[38;5;233m"
        else:
            fg_code = "\x1b[39m"
            
        if bg == 'G':
            bg_code = "\x1b[48;5;220m"
        elif bg == 'B':
            bg_code = "\x1b[48;5;233m"
        else:
            bg_code = "\x1b[49m"
            
    elif mode == '16':
        if fg == 'G':
            fg_code = "\x1b[33m"
        elif fg == 'B':
            fg_code = "\x1b[30m"
        else:
            fg_code = "\x1b[39m"
            
        if bg == 'G':
            bg_code = "\x1b[43m"
        elif bg == 'B':
            bg_code = "\x1b[40m"
        else:
            bg_code = "\x1b[49m"
            
    return fg_code + bg_code

def render_half_block(width, height, left_y_to_x, mode, draw_border=True):
    lines = []
    dx = 500.0 / width
    dy = 580.0 / (2.0 * height)
    
    for row in range(height):
        row_chars = []
        last_fg = None
        last_bg = None
        for col in range(width):
            x = col * dx + dx / 2.0
            y_top = (2 * row) * dy + dy / 2.0
            y_bottom = (2 * row + 1) * dy + dy / 2.0
            
            top_val = get_color(x, y_top, left_y_to_x, draw_border)
            bot_val = get_color(x, y_bottom, left_y_to_x, draw_border)
            
            if mode == 'ascii':
                char = ' '
                if top_val == 'G' and bot_val == 'G':
                    char = '#'
                elif top_val == 'B' and bot_val == 'B':
                    char = '.'
                elif top_val == 'G' and bot_val == 'B':
                    char = '^'
                elif top_val == 'B' and bot_val == 'G':
                    char = 'v'
                elif top_val == 'G':
                    char = '\''
                elif bot_val == 'G':
                    char = ','
                elif top_val == 'B':
                    char = '`'
                elif bot_val == 'B':
                    char = '.'
                row_chars.append(char)
            else:
                fg, bg, char = None, None, " "
                if top_val is None and bot_val is None:
                    fg, bg, char = None, None, " "
                elif top_val == 'G' and bot_val == 'G':
                    fg, bg, char = 'G', None, "█"
                elif top_val == 'B' and bot_val == 'B':
                    fg, bg, char = 'B', None, "█"
                elif top_val == 'G' and bot_val == 'B':
                    fg, bg, char = 'G', 'B', "▀"
                elif top_val == 'B' and bot_val == 'G':
                    fg, bg, char = 'G', 'B', "▄"
                elif top_val == 'G' and bot_val is None:
                    fg, bg, char = 'G', None, "▀"
                elif top_val == 'B' and bot_val is None:
                    fg, bg, char = 'B', None, "▀"
                elif top_val is None and bot_val == 'G':
                    fg, bg, char = 'G', None, "▄"
                elif top_val is None and bot_val == 'B':
                    fg, bg, char = 'B', None, "▄"
                    
                if fg != last_fg or bg != last_bg:
                    ansi = get_ansi_codes(fg, bg, mode)
                    row_chars.append(ansi + char)
                    last_fg = fg
                    last_bg = bg
                else:
                    row_chars.append(char)
        
        row_str = "".join(row_chars)
        if mode != 'ascii':
            row_str += "\x1b[0m"
        lines.append(row_str)
    return "\n".join(lines)

def render_standard_block(width, height, left_y_to_x, mode, draw_border=True):
    lines = []
    dx = 500.0 / width
    dy = 580.0 / height
    
    for row in range(height):
        row_chars = []
        last_fg = None
        last_bg = None
        for col in range(width):
            x = col * dx + dx / 2.0
            y = row * dy + dy / 2.0
            
            val = get_color(x, y, left_y_to_x, draw_border)
            
            if mode == 'ascii':
                char = ' '
                if val == 'G':
                    char = '#'
                elif val == 'B':
                    char = '.'
                row_chars.append(char)
            else:
                fg, bg, char = None, None, " "
                if val is None:
                    fg, bg, char = None, None, " "
                elif val == 'G':
                    fg, bg, char = 'G', None, "█"
                elif val == 'B':
                    fg, bg, char = 'B', None, "█"
                    
                if fg != last_fg or bg != last_bg:
                    ansi = get_ansi_codes(fg, bg, mode)
                    row_chars.append(ansi + char)
                    last_fg = fg
                    last_bg = bg
                else:
                    row_chars.append(char)
                    
        row_str = "".join(row_chars)
        if mode != 'ascii':
            row_str += "\x1b[0m"
        lines.append(row_str)
    return "\n".join(lines)

def get_default_dimensions(mode):
    try:
        columns, lines = shutil.get_terminal_size((80, 24))
    except Exception:
        columns, lines = 80, 24
        
    usable_lines = max(8, lines - 6)
    max_w_chars = int(columns * 0.9)
    
    if mode == 'half':
        # 1:1 aspect ratio per cell since each cell has 2 vertical pixels
        w_chars = int(round(usable_lines * 2.0 * (500.0 / 580.0)))
        h_chars = usable_lines
        
        if w_chars > max_w_chars:
            w_chars = max_w_chars
            h_chars = int(round((w_chars / 2.0) * (580.0 / 500.0)))
    else:
        # 1:2 aspect ratio per cell. We must squish vertical height or stretch width.
        # Visually: character width is roughly 0.5 of character height.
        # To maintain 500:580 aspect ratio: W_chars = H_chars * (500/580) * 2.0
        h_chars = usable_lines
        w_chars = int(round(h_chars * (500.0 / 580.0) * 2.0))
        
        if w_chars > max_w_chars:
            w_chars = max_w_chars
            h_chars = int(round((w_chars / 2.0) * (580.0 / 500.0)))
            
    return w_chars, h_chars

def print_info(mode):
    # Print the beautiful historic and symbolic context
    yellow_ansi = "\x1b[33m" if mode != 'ascii' else ""
    bold_ansi = "\x1b[1m" if mode != 'ascii' else ""
    reset_ansi = "\x1b[0m" if mode != 'ascii' else ""
    
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
    parser = argparse.ArgumentParser(description="Render a beautiful terminal graphic of the Coat of Arms of Furča (Košice - Dargovských hrdinov).")
    parser.add_argument("--width", type=int, help="Width of the graphic in character columns.")
    parser.add_argument("--height", type=int, help="Height of the graphic in character rows.")
    parser.add_argument("--color-mode", choices=['truecolor', '256', '16', 'ascii'], default='truecolor',
                        help="Color mode to use. 'truecolor' (24-bit RGB), '256' (8-bit ANSI), '16' (basic ANSI), or 'ascii' (text art).")
    parser.add_argument("--render-mode", choices=['half', 'standard'], default='half',
                        help="Render resolution mode. 'half' uses unicode half-blocks to double vertical resolution (looks stunning). 'standard' uses full block characters.")
    parser.add_argument("--no-border", action="store_true", help="Do not draw the black shield border.")
    parser.add_argument("--info", action="store_true", help="Print historical and symbolic information about the coat of arms.")
    
    args = parser.parse_args()
    
    # Precompute boundary curve
    left_y_to_x = precompute_bezier()
    
    if args.info:
        print_info(args.color_mode)
        
    # Get dimensions
    if args.width and args.height:
        width, height = args.width, args.height
    elif args.width:
        width = args.width
        if args.render_mode == 'half':
            height = int(round((width / 2.0) * (580.0 / 500.0)))
        else:
            height = int(round(width / 2.0 * (580.0 / 500.0)))
    elif args.height:
        height = args.height
        if args.render_mode == 'half':
            width = int(round(height * 2.0 * (500.0 / 580.0)))
        else:
            width = int(round(height * (500.0 / 580.0) * 2.0))
    else:
        width, height = get_default_dimensions(args.render_mode)
        
    draw_border = not args.no_border
    
    # Print the graphic header
    bold_ansi = "\x1b[1m" if args.color_mode != 'ascii' else ""
    reset_ansi = "\x1b[0m" if args.color_mode != 'ascii' else ""
    
    print(f"\n{bold_ansi}         Coat of Arms of Furča (Košice - Dargovských hrdinov){reset_ansi}\n")
    
    if args.render_mode == 'half':
        graphic = render_half_block(width, height, left_y_to_x, args.color_mode, draw_border)
    else:
        graphic = render_standard_block(width, height, left_y_to_x, args.color_mode, draw_border)
        
    print(graphic)
    print()

if __name__ == "__main__":
    main()
