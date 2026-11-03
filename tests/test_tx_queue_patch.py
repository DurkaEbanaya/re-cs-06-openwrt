"""Test the selector added by patch 0013, with a mocked core selector.

This tests delegation/arguments, not hardware ordering or the kernel core.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class TxQueuePatchTests(unittest.TestCase):
    def test_delegates_to_core_instead_of_executing_cpu(self):
        outer = (REPO / "patches/0013-qcom-ppe-preserve-socket-tx-queue.patch").read_text()
        inner = "\n".join(line[1:] for line in outer.splitlines()
                          if line.startswith("+") and not line.startswith("+++"))
        lines = inner.splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith("@@"))
        body = "\n".join(line[1:] for line in lines[start + 1:]
                         if line.startswith((" ", "+")))
        body = body[:body.index("static int edma_port_open")].strip()
        source = r'''
#include <assert.h>
typedef unsigned short u16;
struct net_device { int id; };
struct sk_buff { int id; };
static struct net_device *wanted_dev, *wanted_sb;
static struct sk_buff *wanted_skb;
static int calls, selected;
static u16 netdev_pick_tx(struct net_device *d, struct sk_buff *s,
                         struct net_device *b) {
 assert(d == wanted_dev && s == wanted_skb && b == wanted_sb);
 calls++; return selected;
}
static u16 selector(struct net_device *netdev, struct sk_buff *skb,
                    struct net_device *sb_dev)
BODY
int main(void) {
 static struct net_device d = {0}, b = {1}; static struct sk_buff s = {0};
 wanted_dev = &d; wanted_skb = &s;
 for (selected = 0; selected < 4; selected++) {
  wanted_sb = &b; assert(selector(&d, &s, &b) == selected);
  wanted_sb = 0; assert(selector(&d, &s, 0) == selected);
 }
 assert(calls == 8);
}
'''
        # The hunk starts with two continued signature lines, followed by {.
        body = body[body.index("{"):]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "test.c").write_text(source.replace("BODY", body))
            subprocess.run(["cc", "-Wall", "-Werror", "-o", str(path / "test"),
                            str(path / "test.c")], check=True)
            subprocess.run([str(path / "test")], check=True)
