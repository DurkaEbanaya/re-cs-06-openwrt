#!/bin/sh
# Opt-in runtime smoke; no WAN/LAN/default-route or owner configuration changes.
set -eu
[ "${1:-}" = --confirm-isolated ] || { echo 'Usage: test-network-support.sh --confirm-isolated' >&2; exit 2; }
[ "$(id -u)" = 0 ] || exit 1
[ "$(cat /tmp/sysinfo/board_name)" = jdcloud,re-cs-06 ] || exit 1
left="r18a-$$"
right="r18b-$$"
table="r18_probe_$$"
made_left=0
made_right=0
made_table=0
work=$(mktemp -d /tmp/r18-probe.XXXXXX)
chmod 700 "$work"
cleanup() {
 [ "$made_table" = 0 ] || nft delete table inet "$table"
 [ "$made_left" = 0 ] || ip netns delete "$left"
 [ "$made_right" = 0 ] || ip netns delete "$right"
 rm -f "$work"/left.key "$work"/left.pub "$work"/right.key "$work"/right.pub
 rmdir "$work"
}
trap cleanup EXIT
trap 'exit 1' INT TERM
ip netns add "$left"
made_left=1
ip netns add "$right"
made_right=1
ip -n "$left" link add test0 type veth peer name test1 netns "$right"
ip -n "$left" addr add 192.0.2.1/30 dev test0
ip -n "$right" addr add 192.0.2.2/30 dev test1
ip -n "$left" link set lo up
ip -n "$right" link set lo up
ip -n "$left" link set test0 up
ip -n "$right" link set test1 up
ip netns exec "$left" ping -c 2 -W 2 192.0.2.2 >/dev/null
echo 'veth and isolated netns: passed'
for pair in wireguard:wg amneziawg:awg; do
 kind=${pair%:*}
 tool=${pair#*:}
 umask 077
 "$tool" genkey > "$work/left.key"
 "$tool" genkey > "$work/right.key"
 "$tool" pubkey < "$work/left.key" > "$work/left.pub"
 "$tool" pubkey < "$work/right.key" > "$work/right.pub"
 ip -n "$left" link add vpn0 type "$kind"
 ip -n "$right" link add vpn0 type "$kind"
 ip netns exec "$left" "$tool" set vpn0 private-key "$work/left.key" listen-port 51820 peer "$(cat "$work/right.pub")" allowed-ips 198.51.100.2/32 endpoint 192.0.2.2:51820
 ip netns exec "$right" "$tool" set vpn0 private-key "$work/right.key" listen-port 51820 peer "$(cat "$work/left.pub")" allowed-ips 198.51.100.1/32 endpoint 192.0.2.1:51820
 ip -n "$left" addr add 198.51.100.1/30 dev vpn0
 ip -n "$right" addr add 198.51.100.2/30 dev vpn0
 ip -n "$left" link set vpn0 up
 ip -n "$right" link set vpn0 up
 ip netns exec "$left" ping -c 3 -W 3 198.51.100.2 >/dev/null
 ip netns exec "$left" "$tool" show vpn0 latest-handshakes | awk '$2 > 0 { found=1 } END { exit !found }'
 echo "$kind: isolated handshake and payload passed (default protocol parameters only)"
 ip -n "$left" link delete vpn0
 ip -n "$right" link delete vpn0
done
ip netns exec "$left" ip tuntap add dev tunprobe mode tun
ip -n "$left" link show tunprobe >/dev/null
echo 'TUN: device creation passed'
# Empty, hookless chain: verifies NFT_QUEUE expression/module only. It cannot
# intercept traffic and is NOT proof of delivery to an NFQUEUE consumer.
nft add table inet "$table"
made_table=1
nft add chain inet "$table" check
nft add rule inet "$table" check queue num 65534 bypass
echo 'NFQUEUE: hookless expression accepted; consumer delivery NOT tested'
echo 'Runtime smoke complete. No cold boot, provider VPN or modem acceptance implied.'
