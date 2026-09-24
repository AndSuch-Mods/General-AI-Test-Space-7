# Machine reporting checklist

Field guide for MM4, MM5 and MM6 production reporting in Siemens TIA Portal and Kepware.

Live app: https://andsuch-mods.github.io/General-AI-Test-Space-7/

The app contains 13 expandable instruction topics, 84 independent checklist tasks, mirrored Completed folders, local notes, export/import of progress, and per-machine Kepware address references. It never connects to a PLC or uploads notes.

## Use

Open `index.html` in a browser, or use the Pages app. Progress is stored in that browser only. Export it before clearing browser storage or moving computers. A supported browser can cache the Pages version for offline use. Resources also provides a standalone HTML download and the reference SCL files.

## Commissioning limits

Reference source is **not compiled in TIA and not tested on a PLC**. Use the installed V15/V16 target help, verify all machine inputs, compile the additions and review the load preview. The observer starts disabled. No machine-specific automatic, communication-valid or abort bit has been guessed. New reporting data only; do not change motion, robot permission, F-logic or existing DB layouts.

MM4/MM5 signal notes derive from the V15 PF1000723 analysis. MM6 derives from the V16 PF1000825 analysis. The live configuration must be checked, particularly MM6's hydraulic selector and robot-input naming conflict. Customer project archives are not stored here.

Shift 1 is 06:30–17:00; shift 2 is 17:00–06:00 the next day. The 06:00–06:30 gap remains unassigned. Count completion in the period containing the finish. Between-cycle waiting is not general machine downtime, and scan-based elapsed counters do not measure CPU STOP/power-off time.

## Rebuild

Python 3 standard library is sufficient:

```sh
python build_content.py
python build_scl.py
python build_html.py
python tests/model_test.py
```

`build_content.py` owns the instructions, tasks and flat export schema. `build_scl.py` generates the legacy and 1500 core/clock references. `app.js` and `style.css` provide interaction and layout. `build_html.py` embeds everything, including source downloads, into `index.html`.

After changing cached content, update the cache version in the service-worker text in `build_html.py`, then rebuild. Preserve localStorage task IDs to keep user progress compatible.

## Tests

`tests/model-results.json`: 23 checks on an independent Python reference model, including 2,400 calendar arithmetic samples. This does not execute or compile Siemens SCL.

`tests/browser-results.json`: 15 Chromium layout/DOM/state checks. The testing container blocks browser navigation, so these used injected documents and a storage test double. Actual native localStorage persistence, service-worker lifecycle and live PLC behavior were not validated by those tests.

The page includes official Siemens/PTC reference links. Installed target-version help and the real download preview take precedence over generic newer online documentation.
