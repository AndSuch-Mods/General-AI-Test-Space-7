# Machine checklist

Live app: https://andsuch-mods.github.io/General-AI-Test-Space-7/

25 short steps for MM4, MM5, MM6 and Kepware. Open **How** under a step for the exact TIA or Kepware clicks. MM6 has 11 monitoring/import/install/check steps. Getting-online tutorials and the long goal explanations have been removed.

The current MM6 download is `downloads/MM6_Reporting_V2.scl`, unchanged from the provided V2 package. Importing it creates the CSI2 reporting tags and logic. It is not compiled in TIA or tested on a PLC. ProductionEligible, RobotDataValid and AbortCycle remain unverified machine mappings. Do not enable until those are resolved. MM4/MM5 do not silently inherit the 1500-specific MM6 source.

## Progress

Current steps move into matching Completed folders and can be restored by unchecking. Browser data stays local. Export/import transfers it between computers. Existing v1 storage is left untouched. Matching monitoring checks migrate; retired checks/notes/configuration remain under Earlier checklist records and in exports. New MM6 V2 install tasks start unchecked, and its new report DB number is not inherited from the old CSI_Report field.

## Rebuild and test

```
python build_html.py
python tests/v2_model_test.py
python tests/checklist_test.py
```

`checklist_data.py` owns the short instructions and stable task IDs. `app.js` and `style.css` own the UI. `schema_v2.json` is checked against the unchanged V2 SCL. `build_html.py` embeds the guide, UI and source download into index.html. The older build_scl.py and legacy source downloads are retained in repository history/files, but are not used by this page or its deployment. Do not regenerate V2 from that old builder.

Browser tests require Playwright and Chromium. CI requires real localhost navigation and tests native persistence, import, cached offline reload, and unchanged source downloads. Restricted local test environments can use the injected-document fallback, explicitly reported in test results. Reference-model tests do not compile or execute Siemens SCL.

The publishing workflow builds/tests the page, commits generated files, publishes only the page/manifest/service worker/current source, then checks the live files byte-for-byte. No machine archives or credentials are published.
