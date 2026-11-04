# LuCI outage: deferred CGI allocation crash

## Cause and reproduction

The pinned uhttpd `2025-10-03-ebb92e6b-1` still returned `int` from
`field_len()`, while the newer libubox `__calloc_a()` consumes variadic lengths
as `size_t`. This mismatch is undefined behavior on the tested aarch64 build.
When the script concurrency limit is reached, `uh_defer_script()` can obtain
a failed allocation and dereference it. LuCI then disappears because the HTTP
server, not just a browser request, has terminated with SIGSEGV (exit 139).
After repeated crashes procd stops respawning it.

This was reproduced on the target using a separate **loopback-only** listener,
temporary CGI root, `-n 1`, and concurrent slow CGI requests. The private core
resolved to `uh_defer_script()` at the `memcpy()` following `calloc_a()`.
The original browser request was not captured, so this establishes the matching
crash mechanism, not the exact request sequence preceding the reported outage.
No production traffic interception, radio reset or proxy policy change was used.

## Fix

[`0023-uhttpd-cgi-size-t.patch`](../patches/0023-uhttpd-cgi-size-t.patch)
backports upstream
[`6ab9abb56bcb28684f382f7a94c170fad02348ea`](https://git.openwrt.org/project/uhttpd.git/commit/?id=6ab9abb56bcb28684f382f7a94c170fad02348ea)
and increments the uhttpd package release to `-2`:

- Match `field_len()` to libubox's `size_t` argument type.
- Handle allocation failures in deferred CGI requests and interpreter setup.
- Additionally install the deferred-request cleanup callback **after** successful
  allocation, so the newly handled OOM path cannot dereference a missing request.

This is a targeted userspace update, not a full uhttpd security audit or an
upstream HEAD upgrade. Existing HTTP authentication, timeouts and concurrency
limits remain unchanged. The full firmware images already published as
**r15-external are not replaced** by this source update and do not contain it.

## Installed scope and acceptance

The patched `uhttpd` and matching `uhttpd-mod-ubus` packages were built with the
pinned aarch64/musl toolchain and installed on the currently used r16 target.
Only uhttpd was restarted; the kernel, network, mobile uplink and HincyRay were
not restarted. The original package files/configuration were backed up privately
on the device and independent storage before replacement.

Candidate isolated regression: **12 slow CGI requests, four concurrent, script
limit one**, all returned HTTP 200 with the expected body. The original binary
terminated with exit 139 on the same deferred-request scenario. The patched
binary SHA256 is
`2e18d5989a522ad37dc4d51f0000783e1c2ad89df45aaad4410a2b22d4f524d8`.

Do not run the crashing original-binary regression against the production LuCI
listener. Keep cores and runtime configuration private; they can contain secrets.
The portable isolated regression helper and operational notes are also recorded
in the owner's separate OpenWRT-ADDON repository.

## Separate Wi-Fi configuration issue

The initial AP startup error (`Invalid country_code '00'`) was independent of
the native HTTP-server crash. A concrete, legally appropriate country and
secured AP configuration are required before enabling a radio. Do not copy a
user's SSID, password or location into public firmware defaults. Wireless
configuration remains owner-provided; this patch changes none of it.
