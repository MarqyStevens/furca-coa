# Furča Coat of Arms - Terminal Renderer

A lightweight, zero-dependency Python script that renders the official Coat of Arms of the Košice borough Dargovských hrdinov (locally known as Furča) directly in the terminal.

The script uses the exact vector mathematics from the official SVG and projects it onto the terminal grid using Unicode half-blocks and 24-bit ANSI TrueColor.

### The Coat of Arms & History
Official heraldic description: *"V zlatom štíte tri čierne kliny"* (In a golden shield, three black wedges/piles).
* **Symbolism:** The three wedges represent the steep slopes and ravines ("úvrate") of the hill the borough is built on. Colors are gold (#FDDA2A) and black (#111111).
* **The Name "Furča":** While officially named after the WWII Battle of Dargov Pass, the historical colloquial name has two main theories:
    1. *Latin origin:* From "furca" (fork), describing the fork-like shape of the forest from old Košice.
    2. *Hungarian origin:* From "furcsa" (weird/strange), tied to old legends of bandit ambushes in the local woods.

### How to Run
Written in pure Python. No external dependencies required.

**Basic scaling (auto-detects terminal size):**
```bash
./render_coa.py
```

**Display graphic with historical context:**
```bash
./render_coa.py --info
```

**Color modes & fallbacks:**
* `--color-mode truecolor` (Default 24-bit RGB)
* `--color-mode 256` (Fallback for older terminals)
* `--color-mode 16` (Basic ANSI)
* `--color-mode ascii` (High contrast, no escape codes)

**Custom dimensions:**
```bash
./render_coa.py --width 50 --height 25
```