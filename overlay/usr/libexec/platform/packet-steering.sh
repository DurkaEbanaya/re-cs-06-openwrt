#!/bin/sh
# Preserve the generic policy, then apply the tested board/conduit override.
flows=$(uci -q get 'network.@globals[0].steering_flows')
case "$flows" in ''|*[!0-9]*) flows=0 ;; esac
if [ "$flows" -gt 0 ]; then
	/usr/libexec/network/packet-steering.uc -l "$flows" "$@" || exit $?
else
	/usr/libexec/network/packet-steering.uc "$@" || exit $?
fi
# An explicit administrator opt-out must retain the generic disabled state.
[ "$1" = 0 ] && exit 0
ACTION=add DEVICENAME=switch sh /etc/hotplug.d/net/90-re-cs-06-rps
