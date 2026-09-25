# This repository is occupied

Maintain the Siemens/Kepware checklist, not another project. The user explicitly asked for fewer words, exact clicks, short checklists and expandable How sections. Do not restore the lengthy getting-online tutorials or generic goals.

Keep Instructions, Programming (MM4, MM5, MM6 and Kepware) and matching Completed folders. Maintain scroll anchoring and local-only progress. Preserve task IDs and v1 saved records. MM6 v2 install IDs are new so old code completion does not imply V2 was installed. Never reuse a saved v1 report DB number for CSI2_Report.

Current source of truth: checklist_data.py, app.js, style.css, schema_v2.json, downloads/MM6_Reporting_V2.scl, build_html.py. The MM6 source is unchanged from the supplied V2 package and has NOT been TIA-compiled or PLC-tested. Old build_scl.py/CSI_ downloads are not the current installation path.

No invented machine addresses, automatic PLC writes, forces, guessed mappings or live downloads. Preserve existing OBs, F-programs and DB layouts. Required ProductionEligible, RobotDataValid and AbortCycle mappings remain unresolved until verified on site. Do not substitute permanent TRUE signals.

Run both the V2 reference-model tests and browser tests before deployment. Publish the current source only; keep customer archives and local notes out of GitHub. A Python model pass is not a Siemens compiler pass.
