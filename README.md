\# Interdigitated Electrode Generator



A Python script that fills a convex outline with interdigitated electrodes and plots the result.



\## Requirements

Python 3 and matplotlib (`pip install matplotlib`)



\## Usage

&#x20;   python ide.py



Enter the outline corners in mm (x,y), one per line, in order around the edge.

Press Enter on an empty line, then set finger width, gap and busbar width.



\## Limitations

\- Convex outlines only

\- Busbar width is measured horizontally, so it is thinner on slanted edges

\- No DXF or GDS export yet

