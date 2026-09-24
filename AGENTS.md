# Project constraints

This repository is occupied by the Siemens/Kepware commissioning checklist. Do not replace it with another project.

Preserve the Instructions, Programming (MM4, MM5, MM6, Kepware) and mirrored Completed hierarchy. Keep checklist IDs stable. Maintain scroll anchoring on expansion and task movement. Progress and notes must remain local, with explicit export/import; do not add analytics or transmit network notes.

Do not introduce machine writes, force operations, invented IPs or unverified PLC addresses. Keep report logic isolated from existing machine/safety programs. Never overwrite existing OB1/OB100 or make existing DBs non-optimized. The code has not been TIA-compiled; do not claim otherwise.

Source of truth: build_content.py, build_scl.py, app.js, style.css and build_html.py. Rebuild index.html after changes and run tests. A Python model pass does not certify SCL compiler compatibility or physical signal behavior. Keep generated report offsets and Kepware reference maps synchronized.

Counting policy: completion-time assignment; shift1 [06:30,17:00), shift2 [17:00,06:00), explicit 06:00–06:30 gap; no midnight reset of night shift. Do not silently invent off-CPU elapsed time or missing production. Preserve validity/partial flags and period keys with counts.
