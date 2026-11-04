# US-location EHT80 AP/STA control

The owner explicitly confirmed that the test devices were physically in
the **United States** before this test. Selecting US was not used as a
regulatory bypass elsewhere. Cleanup restored country **RU** with both
radios disabled, as requested; do not enable them under a country setting
that does not match the actual installation location.

Both full-local r12 routers negotiated **5 GHz, 80 MHz EHT, four spatial
streams**: the AP reported EHT MCS 13 / 2882.3 Mbit/s PHY and the station
reported EHT MCS 12 / 2593.5 Mbit/s TX, with EHT also observed on receive.
This is an actual EHT AP/STA association, not just selecting `EHT80` in UCI.
The previous RU test's NO-EHT restriction remains a separate observation.
Neither current PHY exposes a 6 GHz channel; this is **not Wi-Fi 6E or MLO**.

The wired management chain stayed separate from the routed wireless subnet.
The PC sent through the first router/AP to the second router/STA's radio
address; narrowly scoped SNAT forced the return over Wi-Fi rather than the
management cable. WPA3-SAE and required PMF were used. Requested TX power
was 0 dBm, but received signals remained very strong (roughly -6 to -11 dBm),
so these are close-range laboratory observations, not range/capacity claims.

| r12 mode | PC → STA Mbit/s / TCP retries | STA → PC Mbit/s / TCP retries |
| --- | ---: | ---: |
| Offload disabled | 1386.11 / 467 | 807.49 / 98 |
| Hardware-offload mode | 1325.42 / 0 | 1659.62 / 0 |

Each unidirectional run used two TCP streams for 25 seconds. A subsequent
40-second bidirectional hardware-mode run measured 618.94 / 1188.49 Mbit/s,
with zero TCP retries reported in both directions. Wireless frame failure
counters nevertheless increased; zero TCP retransmissions does not mean
zero MAC retries/loss or a complete radio stability acceptance.

The offload-disabled TCP losses above matched AP softnet backlog drops
exactly. A separate temporary-backlog comparison removed those softnet
drops but left seven reverse TCP retries. A later isolated, loss-traced
repeat localized eight reverse retries to eight fq_codel congestion drops,
with no trace overruns. With ECN negotiated by the PC and routers, another
four software/hardware unidirectional EHT80 runs had zero TCP retries;
the software reverse run recorded seven ECN marks instead of drops.
These are controlled temporary-backlog/endpoint-ECN experiments, not new
universal defaults or a zero-loss guarantee for non-ECN clients.
In that later hardware-mode comparison, valid PPE entries and conntrack
`HW_OFFLOAD` were sampled; PCI-radio Direct Switch was running and not
faulted. This establishes the tested **AP routing path**, not arbitrary
station forwarding or all hardware acceleration features.

All temporary wireless credentials/configuration, NAT and host test routes
were cleaned up after each completed session. Persistent hardware and
software flow-offloading settings returned to disabled. See
[TCP loss diagnosis](TCP-LOSS-DIAGNOSIS.md) for the remaining gates and
excluded overlapping experiments.

## Follow-up on two full r14 devices

After upgrading the first unit and read-only verifying the already-r14
second unit, the same serialized US-location EHT80/NSS4 topology was repeated.
The PC and routers retained ECN setting 2; backlog 16384 was temporary.

| r14 mode | PC → STA Mbit/s / TCP retries | STA → PC Mbit/s / TCP retries |
| --- | ---: | ---: |
| Offload disabled | 1338.30 / 0 | 823.28 / 6 |
| Hardware-offload mode | 1284.11 / 0 | 1644.27 / 0 |

Each run again used two streams for 25 seconds. Six reverse software retries
matched six AP fq_codel congestion-drop trace events; all eight device/run
trace captures had zero overruns. Hardware-mode AP snapshots showed valid
PPE entries, HW_OFFLOAD and running/nonfaulted Direct Switch. Actual rate
samples again included AP EHT MCS13/NSS4 at 2882.3 Mbit/s and STA EHT
MCS12/NSS4 TX at 2593.5 Mbit/s. A first harness attempt stopped before traffic
while waiting for the AP static test address; it is not a benchmark result.
RU/radios-off and original sysctls/configuration were restored, all temporary
test tools/routes/NAT/tracing removed, and both routers had zero AER totals.
See [r14 recheck report](../reports/r14-recheck.json) for the complete scope.
