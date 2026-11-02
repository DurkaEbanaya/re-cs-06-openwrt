# Follow-up: HE negotiation, PCIe, FDB and TCP

These tests used the installed r2 system. No reboot, firmware installation,
bootloader change or regulatory bypass was performed.

## HE: the current test client prevents validation

The AP advertised HE Capabilities and HE Operation in captured scan results,
and hostapd reported `ieee80211ax=1`. The Intel AX201 client's self-managed
RU regulatory rules marked the tested 2.4/5 GHz channels `NO-HE`. The client
therefore associated using VHT on 5 GHz, despite having HE hardware support
and `disable_11ax=N`. Requiring protected management frames produced MFP but
did not change this outcome.

This explains why this client cannot validate HE under its current policy;
it does not establish that every AP HE path works. A different client with
HE permitted on the operating channel is needed. The AP's separate
firmware-derived `NO-EHT` restriction remains unresolved. Neither observation
is a legal determination about all Wi-Fi 6/7 operation in Russia.

Temporary protected APs and the newly created host connection profile were
removed. Both radios were returned to their disabled configuration.

## PCIe: one corrected error, no observed growth

The root-port AER counter remained at one corrected physical-layer RxErr
through repeated association and traffic tests; the endpoint counters
remained zero. This is a boot-time observation on one boot, not proof that
the link can never fail. AER was not disabled, and link speed/ASPM were not
changed simply to hide a warning.

## FDB: candidate source fix, not deployed

`qca8k_fdb_search_and_del()` returns `-EINVAL` when a searched entry has no
aging value (absent/already removed). That error reaches DSA's standalone
host-FDB deletion worker. Shared CPU-port membership can also already be
absent. Patch `0012` makes these deletion-already-complete cases succeed,
without suppressing search/read/purge/reinsert register errors.

This is a candidate explanation/fix for the observed `-22`, not a traced
hardware confirmation of every occurrence. The patch applies in a dry run;
a mocked C control-flow regression test covers deletion and error handling.
The test models the function rather than compiling the actual kernel driver.
The patch has **not been built into or installed on the running router**.
Replacing the live switch driver could sever the management connection.

## TCP: reproduced, not fixed

Two-stream, 15-second endpoint tests over the USB RTL8153 Gigabit adapter:

| Router → computer condition | Receiver Mbit/s | TCP retransmits |
| --- | ---: | ---: |
| CUBIC baseline, run 1 | 870.34 | 468 |
| CUBIC baseline, run 2 | 859.13 | 345 |
| Switch TSO/GSO disabled, run 1 | 863.27 | 247 |
| Switch TSO/GSO disabled, run 2 | 864.63 | 366 |
| Link pause RX/TX enabled, run 1 | 857.14 | 267 |
| Link pause RX/TX enabled, run 2 | 865.61 | 220 |
| Socket pacing, total 800 Mbit/s target | 799.55 | 32 |
| Socket pacing, total 900 Mbit/s target | 897.88 | 101 |

The forward baseline reached 941.26 Mbit/s with zero retransmits. Pacing
substantially reduced retransmits but did not eliminate them. It limits
offered load; it is not a demonstrated full-rate fix. Disabling switch
segmentation and enabling pause did not fix the issue and were reverted.
An attempted BBR comparison was rejected by the test host before producing
valid traffic; it must not be counted as a BBR result.

Router MAC/FCS/overflow counters did not explain the losses. The host USB
adapter had small cumulative error counts without a reliable pre-test delta,
so their causal significance is unknown. A host GRO change was denied by
permissions and was not applied. Queue-limit experiments produced no valid
result and their temporary settings were restored. Do not attribute this
problem conclusively to the router, USB adapter or cable without another
receiver/adapter and synchronized counter or packet-capture evidence.

All applied offload, pause and queue changes were restored. The test server
was stopped and removed; WAN remains disabled. The normal host internet
connection was not moved to the experimental router. No global congestion
control change or permanent pacing workaround was installed.
