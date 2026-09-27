# This repository is occupied

Maintain the Siemens/Kepware checklist, not another project. The user explicitly asked for fewer words, exact clicks, short checklists and expandable How sections. Do not restore the lengthy getting-online tutorials or generic goals.

Keep Instructions, Programming (MM4, MM5, MM6 and Kepware) and matching Completed folders. Maintain scroll anchoring and local-only progress. Preserve task IDs and v1 saved records. MM6 v2 install IDs are new so old code completion does not imply V2 was installed. Never reuse a saved v1 report DB number for CSI2_Report.

Current source of truth: checklist_data.py, app.js, style.css, schema_v2.json, downloads/MM6_Reporting_V2.scl, build_html.py. The MM6 source is unchanged from the supplied V2 package and has NOT been TIA-compiled or PLC-tested. Old build_scl.py/CSI_ downloads are not the current installation path.

No invented machine addresses, automatic PLC writes, forces, guessed mappings or live downloads. Preserve existing OBs, F-programs and DB layouts. Required ProductionEligible, RobotDataValid and AbortCycle mappings remain unresolved until verified on site. Do not substitute permanent TRUE signals.

Run both the V2 reference-model tests and browser tests before deployment. Publish the current source only; keep customer archives and local notes out of GitHub. A Python model pass is not a Siemens compiler pass.

Manual-build route: the user now wants to enter code manually. Keep exact UI clicks, declaration tables and body-only SCL pieces. manual_steps.py patches build_data without altering the V2 source. Do not revert to source import as the main checklist task. CSI is an optional folder; CSI_Reporting is the new main FB. Verify names in TIA before creation. Preserve retired v3 progress under Earlier checklist records. Run the manual structure/browser tests and existing V2 model tests.

## CSI naming and checklist identity

The active manual route now uses CSI_Report, CSI_Setup, CSI_Reporting, CSI_Reporting_DB, CSI_Run, CSI_Startup and CSI_ helpers. csi_branding.py applies a symbol-only mapping after manual_steps.py; field offsets, schema version 2 and all executable behavior are unchanged. The immutable V2 file is retained for derivation/tests only. The optional current source is downloads/MM6_CSI_Reporting.scl, not the old import route. Do not restore CSI2 names in the active page or copied code.

The clipboard/checkmark identity is provided as SVG favicon, PNG favicon, iOS touch icon and installable-app icons. csi_theme.css styles the existing compact checklist without adding tasks. Keep the existing localStorage key, task IDs, notes and recorded DB fields; verify a recorded number belongs to CSI_Report before using it. Test scrolling, persistence, copying and offline operation. Do not change billing settings or enable paid runners. The publishing workflow retains no extra screenshot artifacts.
