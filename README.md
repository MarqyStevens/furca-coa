# 🛡️ Furča Coat of Arms Terminal Renderer

A highly accurate, interactive, and beautifully designed terminal graphics engine that renders the official **Coat of Arms of the Košice borough of Dargovských hrdinov** (famously known as **Furča**), located in Slovakia.

This engine utilizes the exact vector mathematics of the official SVG source file from Wikimedia Commons, projecting it onto a discrete terminal grid using advanced sub-pixel rendering (Unicode half-blocks) and full 24-bit ANSI TrueColor.

---

## 🎨 Symbolism & History

The coat of arms is defined in Slovak heraldry as:
> **"V zlatom štíte tri čierne kliny"** *(In a golden shield, three black wedges/piles)*.

### 📐 The Geometry
* **The Three Black Wedges:** A stylized and geometric representation of the **"úvrate"** (ravines, steep slopes, or cuts) that carve into the hill upon which the borough is built.
* **The Colors:** A striking contrast of gold (`#FDDA2A`) and deep charcoal black (`#111111`).

### 📜 The Legends of "Furča"
While the official name **Dargovských hrdinov** (Dargov Heroes) honors the fierce World War II Battle of Dargov Pass (January 1945), locals almost exclusively call the borough **Furča**. Two fascinating theories explain this name:
1. **The Latin Theory (Historical):** Derived from the Latin *furca* (fork/vidlica). From old Košice, the forest atop the hill had a distinct fork-like shape. Medieval German settlers brought similar names (*Furche*, *Fourche*) from the Rhineland.
2. **The Hungarian Theory (Folk Legend):** Derived from the Hungarian *furcsa* (strange/weird), stemming from old tales of mysterious occurrences and bandit ambushes in the deep forests.

---

## 🚀 How to Run

The renderer is written in pure Python with zero external dependencies, making it extremely lightweight and portable.

### 1. Execute Directly
Simply run the script. By default, it will **automatically detect your terminal window size** and scale the graphic to fit perfectly:
```bash
./render_coa.py
```

### 2. View History and Details
To display the gorgeous, formatted historical details alongside the graphic, use the `--info` flag:
```bash
./render_coa.py --info
```

### 3. Change Color Modes
If your terminal doesn't support 24-bit color, the script supports robust fallbacks:
* **TrueColor (Default):** `./render_coa.py --color-mode truecolor` (Stunning 24-bit RGB)
* **256-Color ANSI:** `./render_coa.py --color-mode 256` (Great for older terminals)
* **16-Color ANSI:** `./render_coa.py --color-mode 16` (Basic compatibility)
* **Pure ASCII Art:** `./render_coa.py --color-mode ascii` (High contrast, no escape codes)

### 4. Adjust Dimensions
You can override the automatic scaling and specify custom dimensions:
```bash
./render_coa.py --width 50 --height 25
```

---

## 📂 File Structure

* **`render_coa.py`**: The core rendering engine, utilizing cubic Bezier formulas to project the shield and geometric wedges.
* **`coa.svg`**: The original, high-resolution official vector SVG file downloaded from Wikimedia Commons.
* **`README.md`**: This guide.

*Created with 💛 for Košice and the beautiful history of Furča.
