# Interdigitated Electrode Generator

A Python tool that fills a convex outline with two interlocking (interdigitated) electrodes, previews the design and exports it. All dimensions are in millimetres.

## Features
- Any convex outline, entered as corner points
- Adjustable finger width, gap and busbar width
- Reports the smallest gap between the two electrodes
- Preview before export
- Export to PDF, SVG, EPS, PNG, JPG, TIFF, DXF, Gerber, GDSII and CSV

## Requirements
- Python 3
- matplotlib

```
pip install matplotlib
```

## Usage
```
python ide.py
```

1. Enter the corners in order around the edge as `x,y`, one per line.
2. Press Enter on an empty line.
3. Enter the finger width, gap and busbar width, or press Enter for the defaults.
4. Close the preview window.
5. Choose the export formats and a file name.

### Example: 10 × 10 mm square
```
Corner 1: 0,0
Corner 2: 10,0
Corner 3: 10,10
Corner 4: 0,10
Corner 5:
```

| Parameter | Default (mm) |
|---|---|
| Finger width | 0.3 |
| Gap | 0.3 |
| Busbar width | 0.8 |

## Export formats
| Format | Notes |
|---|---|
| PDF, SVG, EPS | Vector drawings at true size with a 5 mm margin. Print at 100%. |
| PNG, JPG, TIFF | Images, up to 1200 dpi |
| DXF | One closed, unfilled outline per electrode, on separate layers |
| Gerber (`.gbr`) | Electrode copper shapes only |
| GDSII (`.gds`) | Electrodes on layers 1 and 2 |
| CSV | Corner coordinates of each electrode |

## Limitations
- Outlines with inward dents are not supported
- No contact pads
- Busbar width is measured horizontally, so busbars are thinner on slanted edges and can taper to points on round shapes
- Very narrow parts of an outline are left empty
- Gerber output has no board outline or solder mask
- DXF, Gerber and GDSII output has not yet been verified in CAD or fabrication software. Inspect files in a viewer before manufacturing.
