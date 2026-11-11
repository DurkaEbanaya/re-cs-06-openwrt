#!/bin/sh
# Install optional packages deliberately before this test. Never configures SQM
# or attaches a qdisc/firewall hook to an owner's interface.
set -eu
[ "${1:-}" = --confirm-isolated ] || { echo 'Usage: test-optional-support.sh --confirm-isolated' >&2; exit 2; }
[ "$(id -u)" = 0 ] || exit 1
[ "$(cat /tmp/sysinfo/board_name)" = jdcloud,re-cs-06 ] || exit 1
namespace="r19opt-$$"
created=0
cleanup() { [ "$created" = 0 ] || ip netns delete "$namespace"; }
trap cleanup EXIT
trap 'exit 1' INT TERM
ip netns add "$namespace"
created=1
ip -n "$namespace" link set lo up
ip -n "$namespace" link add base0 type veth peer name base1
ip -n "$namespace" addr add 192.0.2.1/30 dev base0
ip -n "$namespace" link set base0 up
ip -n "$namespace" link add dummy0 type dummy
ip -n "$namespace" link add link base0 ipvlan0 type ipvlan mode l2
ip netns exec "$namespace" ip tunnel add ipip0 mode ipip local 192.0.2.1 remote 192.0.2.2
ip netns exec "$namespace" ip tunnel add gre0test mode gre local 192.0.2.1 remote 192.0.2.2
ip -n "$namespace" link add gretap0 type gretap local 192.0.2.1 remote 192.0.2.2
ip -n "$namespace" link add gre6test type ip6gre local 2001:db8::1 remote 2001:db8::2
ip -n "$namespace" link add gre6tap type ip6gretap local 2001:db8::1 remote 2001:db8::2
ip netns exec "$namespace" ip tunnel add sit0test mode sit local 192.0.2.1 remote 192.0.2.2
ip -n "$namespace" link add vxlan0 type vxlan id 19 remote 192.0.2.2 dev base0 dstport 4789
ip -n "$namespace" link add ifb0 type ifb
ip -n "$namespace" link set ifb0 up
ip netns exec "$namespace" tc qdisc add dev ifb0 root cake bandwidth 10mbit
ip netns exec "$namespace" tc qdisc show dev ifb0 | grep -q 'cake'
ip netns exec "$namespace" nft add table inet probe
ip netns exec "$namespace" nft add chain inet probe check
ip netns exec "$namespace" nft add rule inet probe check meta l4proto tcp socket transparent 1 counter
echo 'Optional devices, isolated CAKE and hookless socket expression: passed'
echo 'No SQM on owner interfaces, tunnel payload/throughput, bridge filtering or filesystem mount acceptance implied.'
