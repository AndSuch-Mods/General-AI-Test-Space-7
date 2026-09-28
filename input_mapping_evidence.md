# Reporting call inputs: source evidence and limits

Reviewed 28 September 2026. These are read-only observations from the two supplied offline archives, not an upload from a running PLC. The five English input names belong to our CSI reporting FB. They are not five pre-existing Siemens or machine tags.

## What each input means

| CSI input | Meaning when TRUE |
|---|---|
| CloseCommand | The machine is commanding mold closing. Use its rising edge, not its ON duration as the whole cycle. |
| RobotPermit | The robot interface permits mold closing. A low state followed by its return high is the proposed end event. |
| ProductionEligible | The operating mode is one whose cycles we intend to count. This is not necessarily a running/motor bit. |
| RobotDataValid | The observed robot input data are available and trustworthy. This is not the same as robot-clear, robot-in-auto, motors-on, or robot-ready. |
| AbortCycle | Discard an unfinished observation because a cycle-cancel/reset condition applies. It does not command the machine to abort. |

## Direct event inputs

MM6 FC200 network 10 copies I705.7 into DB94.DBX29.6, named `DB Digitale Eingänge.EUROMAP_FreigabeFormSchliessen`. English: digital inputs, EUROMAP permission to close the mold. MM6 FC452 network 27 writes DB98.DBX112.7, named `DB Digitale Ausgänge 2.stt_Hyd_REXROTH_Ventil_FormSchliessen.Ausgang`, and Q34.0. English: digital outputs 2, Rexroth hydraulic mold-closing valve, output.

The first archive used as the MM4/MM5 reference copies I505.7 into DB94.DBX29.4 in FC200 saved network 10, then into DB207.DBX0.0 in FC166 saved network 1. FC452 saved network 27 writes DB98.DBX112.7 and Q44.0.

| Input | MM4/MM5 reference archive | MM6 archive |
|---|---|---|
| CloseCommand | DB98.DBX112.7 | DB98.DBX112.7 |
| RobotPermit | DB94.DBX29.4 | DB94.DBX29.6 |

## Production mode sources found in both archives

MM6 FC41 `Modeumschaltung` network 8, compile-unit object 428699, PEData.plf offset 16065852, assigns these mutually selected mode bits after clearing MB50:

| Address | MM6 symbol | English |
|---|---|---|
| M50.0 | Mode Hand | Manual individual operation |
| M50.1 | Mode Handtakt | Manual step/cycle mode |
| M50.2 | Mode Halbautomat | Semiautomatic mode |
| M50.3 | Mode Automat | Automatic mode |
| M50.4 | Mode Grundstellung | Return to base/home position |
| M50.5 | Mode Vorheizen | Preheating |
| M50.6 | Mode Werkzeugwechsel | Tool change |

In the same network M50.2 is assigned with displayed mode 2 at DB88.DBW12; M50.3 is assigned with displayed mode 3. The first archive's FC41 saved network 8, object 463368, offset 4535052, contains the same MB50/M50.2/M50.3 assignments and displayed mode numbers.

Proposed reporting policy, not an existing combined machine tag: `ProductionEligible = M50.2 OR M50.3`. This counts semiautomatic and automatic production, and deliberately excludes the manual Hand/Handtakt, homing, preheat and tool-change modes. For automatic-only reporting, M50.3 alone is the corresponding mode bit. Confirm the desired mode policy and the live values; do not alter the original mode bits.

FC166 also broadcasts a wider mode combination including M50.1 to the robot. That broader combination should not be silently substituted when manual stepping is meant to be excluded.

## A definite machine-sequencer reset source

MM6 FC40 network 14, object 428312, offset 15502657, begins its sequencer-reset expression with `O DB20.DBX0.1`, symbol `DB Störungen.Klasse_1_NotStop`, and writes the result to local `SchaltwerkReset` and DB180.DBX20.0. English: fault DB, class-1 immediate-stop condition; sequencer reset.

The first archive's FC40 saved network 14, object 463335, offset 4514608, begins the equivalent reset expression with the same DB20.DBX0.1. This is an archive-supported candidate for the reporting AbortCycle input on both project families. It is a standard-program fault/reset indicator, not a safety-rated signal and not proof that every possible robot reset/cancel is covered.

DB20.DBX0.2 is `Klasse_2_SK_Steh` (class-2 sequencer standstill); DB20.DBX0.3 is `Klasse_3_kein_Neustart` (class-3 inhibit new start). FC40 network 7 resets M40.4 `Automat_Start` for several conditions. Therefore NOT M40.4, every warning, and ordinary waiting are not substitutes for a cycle-cancel input. Do not use the whole `SchaltwerkReset` expression as AbortCycle without review: it also includes normal end-of-sequence handling.

## RobotDataValid: no existing one-bit mapping has been verified

MM6 FC900 `RobotMain` network 2 connects these input statuses to FB900 `ABB_Controller`, instance DB900:

| Address | Existing pin | Meaning |
|---|---|---|
| I700.4 | AutoOn | Robot automatic-mode status |
| I700.5 | RunChainOK | Robot run-chain status |
| I700.6 | ExecutionError | Robot program execution error |

None of these is a proven PROFINET input-data-valid bit. FB900's OK_ToStart expression also requires the motors-off state, so it is not a valid always-needed qualification while a normal cycle runs.

MM6 has a cyclic DeviceStates call in FC10 network 16 (object 427941, offset 15119181), MODE 5, LADDR 257. Its status return is a local temporary variable. The presence of that call or a zero in its stored bit array is not, by itself, a verified continuously successful robot-specific quality result.

The archive's hardware metadata contains system constant `RobotBasicIO~DI_32_bytes_1`, type HW_SUBMODULE, value 302 (object 477385), attached to the ABB robot DI 32-byte submodule. It also contains `RobotBasicIO~IODevice` HW_DEVICE 314 and `Local~PROFINET_IO-System` HW_IOSYSTEM 257. These are candidates for a new read-only diagnostic query, not permission to assume the current hardware IDs or I/O address mapping. Confirm in the current device overview that the selected DI module includes I705.7 before using it.

A possible MM6 implementation is GET_DIAG MODE 1 on that verified input-submodule system constant, with a DIS result. Accept data only when the call returns 0 and the DIS IOState Good bit is set. This reads transport/module health; it does not prove the robot's application task is advancing or that a part was picked. This additional query has not been compiled or tested here. It belongs before the reporting FB call and writes only new local diagnostic variables.

The legacy reference uses RDSYSST in FC20 (SZL_ID 16#0694, INDEX 16#0064, RET_VAL DB7.DBW0, BUSY DB7.DBX2.0, data buffer DB7). The particular robot station entry, return/busy handling and freshness have not been established. Do not copy MM6 hardware ID 302, use I500.x by analogy, or label RunChainOK as data-valid on MM4/MM5. Their exact RobotDataValid operand is still unresolved.

## Provenance

- MM6 original: PF1000825_20260909_0943.zap16, SHA256 `15b05669e3f7e615f6bf1799d6ac017531eca910f9b98d62291124e21a6d4f37`.
- MM4/MM5 reference: PF1000723_F_20260909_0943.zap15, SHA256 `45de7c6600492c343736d4617a1f59eea69f07c7b8525c3f7336e80184797c46`.
- Custom reconstructed network text was checked against the supplied extraction package and its archive identity. It is not a Siemens-certified export. MM4's live screenshot showed another project name, PF1000690_B_V16; live equivalence is not established by the reference archive.
- No customer project archive, machine connection, PLC write, forcing or download is part of this update.

Official instruction reference: https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/diagnostics-s7-1200-s7-1500/get_diag-read-diagnostic-information-s7-1200-s7-1500
