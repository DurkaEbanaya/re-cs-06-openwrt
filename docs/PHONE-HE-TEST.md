# Wi-Fi 6 acceptance with an independent phone client

A USB/ADB-connected Android phone was used as a Wi-Fi client, not as a USB
network adapter. On the existing configured regulatory domain, a temporary
WPA2-CCMP AP used channel 36, HE80 and 10 dBm configured power. No country
spoofing or regulatory bypass was performed.

Both Android Wi-Fi status (`11ax`) and the router's station status
(`HE-MCS`, two spatial streams; hostapd `he:true`) confirmed HE negotiation.
The phone obtained a DHCP lease. Two TCP streams for 20 seconds delivered:

| Direction | Receiver Mbit/s | Sender retransmits |
| --- | ---: | ---: |
| Phone → router | 440.75 | 0 |
| Router → phone | 558.65 | 39 |

The ADB shell initially selected cellular data because the isolated test AP
has no internet. The valid tests explicitly bound iperf to the Wi-Fi device
and its local address; no phone VPN/mobile routing policy was changed.
The test executable was statically linked for Android compatibility.

This establishes actual 802.11ax data transfer on **5 GHz**, not maximum
range/rate, 2.4 GHz HE, 160 MHz, Wi-Fi 7, MLO or a 6 GHz radio. The current
RE-CS-06 PHYs advertise 2.4 and 5 GHz only. Wi-Fi 6 and the 6 GHz band are
different concepts; there is no 6 GHz AP in the current hardware/driver
configuration to test with this phone.

The temporary phone network and executable were removed. The router's
previous disabled Wi-Fi configuration was restored. Known vendor radio
firmware remains necessary; these results do not change its licensing.
