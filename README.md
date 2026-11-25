# Furča Coat of Arms - Terminal Renderer

A lightweight, zero-dependency Python script that renders the official Coat of Arms of the Košice borough Dargovských hrdinov (locally known as Furča) directly in the terminal or as a high-res PNG.

The script uses the exact vector mathematics from the official SVG and renders it with anti-aliased TrueColor sub-blocks, dense Unicode block grids, or native terminal pixel protocols.

### The Coat of Arms & History
Official heraldic description: *"V zlatom štíte tri čierne kliny"* (In a golden shield, three black wedges/piles).
* **Symbolism:** The three wedges represent the steep slopes and ravines ("úvrate") of the hill the borough is built on. Colors are gold (#FDDA2A) and black (#111111).
* **The Name "Furča":** While officially named after the WWII Battle of Dargov Pass, the historical colloquial name has two main theories:
    1. *Latin origin:* From "furca" (fork), describing the fork-like shape of the forest from old Košice.
    2. *Hungarian origin:* From "furcsa" (weird/strange), tied to old legends of bandit ambushes in the local woods.

### How to Run
Written in pure Python. No external dependencies required.

**Basic scaling (auto-detects terminal size, sharp TrueColor half-blocks):**
```bash
./render_coa.py
```

**Higher-density Unicode text modes (more pixels per terminal cell):**
* `--render-mode half` (1×2 pixels/cell, sharp by default)
* `--render-mode quadrant` (2×2 = 4 pixels/cell, universal Unicode blocks)
* `--render-mode sextant` (2×3 = 6 pixels/cell, Unicode 13 Legacy Computing blocks)
* `--render-mode standard` (1×1 full blocks)

**True high-res pixel protocols & PNG export:**
* `--render-mode kitty` (Kitty / Ghostty / WezTerm / Konsole inline PNG)
* `--render-mode iterm2` (iTerm2 / WezTerm inline PNG)
* `--render-mode sixel` (xterm / Foot / WezTerm / Windows Terminal Sixel raster)
* `--save-png furca.png --pixel-width 2000` (save a transparent anti-aliased PNG)

**Display graphic with historical context:**
```bash
./render_coa.py --info
```

**Color modes & anti-aliasing:**
* `--color-mode truecolor` (Default 24-bit RGB)
* `--color-mode 256` (Fallback for older terminals)
* `--color-mode 16` (Basic ANSI)
* `--color-mode ascii` (High contrast, no escape codes)
* `--aa 4` (NxN supersampling factor; defaults to `1` for sharp text blocks and `4` for pixel/PNG modes)
* `--bg #1e1e2e` (Blend the outer shield border into a known terminal background color)

**Custom dimensions:**
```bash
./render_coa.py --width 50 --height 25
./render_coa.py --render-mode sextant --width 80
./render_coa.py --render-mode kitty --pixel-width 1500
```
