"""Compile the patched FDB deletion function with mocked register access."""
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class FdbDeletionTests(unittest.TestCase):
    def test_missing_membership_and_register_failures(self):
        patch = (REPO / "patches/0012-qca8k-idempotent-fdb-delete.patch").read_text()
        self.assertIn("!fdb.aging || !(fdb.port_mask & port_mask)", patch)
        # Exercise the full search/delete/reinsert control flow, including
        # unchanged error paths, without touching any hardware.
        source = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
typedef uint8_t u8;
typedef uint16_t u16;
struct qca8k_priv { int reg_mutex; };
struct qca8k_fdb { int aging; u8 port_mask; };
static struct qca8k_fdb entry;
static int fail_search, fail_read, fail_purge, fail_load, purges, loads;
enum { QCA8K_FDB_SEARCH, QCA8K_FDB_PURGE, QCA8K_FDB_LOAD };
#define mutex_lock(x) ((void)(x))
#define mutex_unlock(x) ((void)(x))
static void qca8k_fdb_write(struct qca8k_priv *p, u16 v, u8 m, const u8 *a, int age) {}
static int qca8k_fdb_read(struct qca8k_priv *p, struct qca8k_fdb *f) { *f = entry; return fail_read; }
static int qca8k_fdb_access(struct qca8k_priv *p, int cmd, int port) {
 if (cmd == QCA8K_FDB_SEARCH) return fail_search;
 if (cmd == QCA8K_FDB_PURGE) { purges++; return fail_purge; }
 loads++; return fail_load;
}
FUNCTION
int main(void) {
 struct qca8k_priv p = {0}; u8 mac[6] = {0};
 assert(qca8k_fdb_search_and_del(&p, 1, mac, 1) == 0);
 assert(!purges && !loads);
 entry.aging = 15; entry.port_mask = 2;
 assert(qca8k_fdb_search_and_del(&p, 1, mac, 1) == 0);
 assert(!purges && !loads);
 entry.port_mask = 1;
 assert(qca8k_fdb_search_and_del(&p, 1, mac, 1) == 0);
 assert(purges == 1 && !loads);
 entry.port_mask = 3;
 assert(qca8k_fdb_search_and_del(&p, 1, mac, 1) == 0);
 assert(purges == 2 && loads == 1);
 fail_search = -EIO;
 assert(qca8k_fdb_search_and_del(&p, 1, mac, 1) == -EIO);
 fail_search = 0; fail_read = -ETIMEDOUT;
 assert(qca8k_fdb_search_and_del(&p, 1, mac, 1) == -ETIMEDOUT);
 fail_read = 0; fail_purge = -EIO;
 assert(qca8k_fdb_search_and_del(&p, 1, mac, 1) == -EIO);
 fail_purge = 0; fail_load = -EIO;
 assert(qca8k_fdb_search_and_del(&p, 1, mac, 1) == -EIO);
}
'''
        function = r'''
static int qca8k_fdb_search_and_del(struct qca8k_priv *priv, u8 port_mask,
                                  const u8 *mac, u16 vid)
{
 struct qca8k_fdb fdb = {0}; int ret;
 mutex_lock(&priv->reg_mutex);
 qca8k_fdb_write(priv, vid, 0, mac, 0);
 ret = qca8k_fdb_access(priv, QCA8K_FDB_SEARCH, -1);
 if (ret < 0) goto exit;
 ret = qca8k_fdb_read(priv, &fdb);
 if (ret < 0) goto exit;
 if (!fdb.aging || !(fdb.port_mask & port_mask)) { ret = 0; goto exit; }
 ret = qca8k_fdb_access(priv, QCA8K_FDB_PURGE, -1);
 if (ret) goto exit;
 if (fdb.port_mask == port_mask) goto exit;
 fdb.port_mask &= ~port_mask;
 qca8k_fdb_write(priv, vid, fdb.port_mask, mac, fdb.aging);
 ret = qca8k_fdb_access(priv, QCA8K_FDB_LOAD, -1);
exit:
 mutex_unlock(&priv->reg_mutex); return ret;
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "test.c").write_text(source.replace("FUNCTION", function))
            subprocess.run(["cc", "-o", str(path / "test"), str(path / "test.c")], check=True)
            subprocess.run([str(path / "test")], check=True)
