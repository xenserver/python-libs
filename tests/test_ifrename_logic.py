# pyright: reportGeneralTypeIssues=false,reportAttributeAccessIssue=false
# pytype: disable=attribute-error
from __future__ import print_function
from __future__ import unicode_literals
import logging
import sys
import unittest
from copy import deepcopy

from io import StringIO

# pylint:disable=wildcard-import,unused-wildcard-import,invalid-name,use-implicit-booleaness-not-len
from xcp.net.ifrename.logic import *
from xcp.logger import openLog, closeLogs

def apply_transactions(lst, trans):

    if not len(trans):
        raise LogicError("No transactions")

    for (src, dst) in trans:
        for e in lst:
            if e.tname and e.tname == src:
                e.tname = dst
                break
            if e.kname == src:
                if e.tname is not None:
                    raise LogicError("Matched kname with non-null tname. %s"
                                     % (locals(),))
                e.tname = dst
                break
        else:
            raise LogicError("Not found suitable eth for transaction. %s"
                             % (locals(),))

class TestSimpleLogic(unittest.TestCase):

    def setUp(self):
        self.siobuff = StringIO()
        openLog(self.siobuff, logging.NOTSET)

    def tearDown(self):

        closeLogs()
        self.siobuff.close()

    def debug_state(self, ts):
        print("", file=sys.stderr)
        print(self.siobuff.getvalue(), file=sys.stderr)
        print("", file=sys.stderr)
        if len(ts):
            for (s,d) in ts:
                print("'%s' -> '%s'" % (s, d), file=sys.stderr)
        else:
            print("No transactions", file=sys.stderr)
        print("", file=sys.stderr)


    def test_newhw_norules_1eth(self):
        """
        One previously unrecognised nic, with no other rules.  Expecting
        it to be named as eth0
        """

        eth0 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0","side-12-eth1")
        cur_state = [eth0]

        ts = rename_logic([],
                          deepcopy(cur_state),
                          [],
                          [])

        self.assertTrue(len(ts) == 1)
        apply_transactions(cur_state, ts)
        self.assertTrue(eth0.tname == "eth0")

    def test_newhw_norules_2eth(self):
        """
        Two previously unrecognised nics, with no other rules.  Expecting
        them to be renamed to eth0 and 1 respectively
        """

        eth0 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0","side-12-eth1")
        eth1 = MACPCI("aa:cd:ef:12:34:56","0000:00:01.0","side-33-eth0")
        cur_state = [eth0, eth1]

        ts = rename_logic([],
                          deepcopy(cur_state),
                          [],
                          [])

        self.assertTrue(len(ts) == 2)
        apply_transactions(cur_state, ts)
        self.assertTrue(eth0.tname == "eth0")
        self.assertTrue(eth1.tname == "eth1")

    def test_newhw_1srule_1eth(self):
        """
        One previously unrecognised nic with a static rule referring to it.
        Expecting it to be named to eth0 as per the static rule.
        """

        eth0 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", "side-12-eth1")
        srule_eth0 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", None, "eth0")
        cur_state = [eth0]

        ts = rename_logic([srule_eth0],
                          deepcopy(cur_state),
                          [],
                          [])

        self.assertTrue(len(ts) == 1)
        apply_transactions(cur_state, ts)
        self.assertTrue(eth0.tname == "eth0")

    def test_newhw_2srule_1eth(self):
        """
        One previously recognised nic with two static rules.  Expecting
        the nic to be renamed from eth1 to eth0 to fall in line with the static
        rule
        """

        cur_eth0 = MACPCI("12:34:56:78:90:12","0000:00:01.0", "eth0")
        srule_eth0 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", None, "eth0")
        srule_eth1 = MACPCI("12:34:56:78:90:12","0000:00:01.0", None, "eth1")
        cur_state = [cur_eth0]

        ts = rename_logic([srule_eth0, srule_eth1],
                          deepcopy(cur_state),
                          [],
                          [])

        self.assertTrue(len(ts) == 1)
        apply_transactions(cur_state, ts)

        self.assertTrue(cur_eth0.tname == "eth1")

    def test_newhw_2srule_2eth(self):
        """
        Two nics, one recognised and one not, with two static rules.
        Expecting 2 or 3 transactions (depending on the logic) resulting
        in the currently named eth0 changing name to eth1, and the currently
        sideways nic to be named eth0
        """

        cur_eth0 = MACPCI("12:34:56:78:90:12","0000:00:01.0", "eth0")
        cur_eth1 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", "side-12-eth1")
        srule_eth0 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", None, "eth0")
        srule_eth1 = MACPCI("12:34:56:78:90:12","0000:00:01.0", None, "eth1")
        cur_state = [cur_eth0, cur_eth1]

        ts = rename_logic([srule_eth0, srule_eth1],
                          deepcopy(cur_state),
                          [],
                          [])


        self.assertTrue(len(ts) == 3 or len(ts) == 2)
        apply_transactions(cur_state, ts)

        self.assertTrue(cur_eth0.tname == "eth1")
        self.assertTrue(cur_eth1.tname == "eth0")

    def test_nosrules_1eth_incorrect_udev(self):
        """
        One currently unrecognised nic which has an entry in last state
        information.  It should be renamed as per the last state entry to eth3
        """

        cur_eth0 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", "side-12-eth0")
        last_eth3 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", None, "eth3")
        cur_state = [cur_eth0]

        ts = rename_logic([],
                          deepcopy(cur_state),
                          [last_eth3],
                          [])

        # Expecting 1 transactions
        self.assertTrue(len(ts) == 1)
        apply_transactions(cur_state, ts)

        self.assertTrue(cur_eth0.tname == "eth3")

    def test_nosrules_1eth_correct_udev(self):
        """
        One recognised nic which also has a last state entry. This is the
        default condition for rebooting the server without changing hardware,
        and 0 transactions should take place.
        """

        cur_eth1 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", "eth1")
        last_eth1 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", None, "eth1")
        cur_state = [cur_eth1]

        ts = rename_logic([],
                          deepcopy(cur_state),
                          [last_eth1],
                          [])

        # Expecting 0 transactions
        self.assertTrue(len(ts) == 0)

    def test_1srule_1eth_1last_correct_udev(self):
        """
        One recognised nic, in line with its last state entry, but a (new)
        static rule which has a different idea for it.  Expecting it to be
        renamed to eth0 as per the static rule
        """

        cur_eth1 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", "eth1")
        srule_eth0 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", None, "eth0")
        last_eth1 = MACPCI("ab:cd:ef:12:34:56","0000:00:0f.0", None, "eth1")
        cur_state = [cur_eth1]

        ts = rename_logic([srule_eth0],
                          deepcopy(cur_state),
                          [last_eth1],
                          [])

        # Expecting 1 transactions
        self.assertTrue(len(ts) == 1)
        apply_transactions(cur_state, ts)

        self.assertTrue(cur_eth1.tname == "eth0")

    def test_1srule_1eth_already_complete(self):
        """
        One recognised nic, and a static rule for that nic.  Expecting no
        transactions at all.
        """

        cur_eth0 = MACPCI("00:13:72:2d:2a:ec", "0000:04:00.0", "eth0")
        srule_eth0 = MACPCI("00:13:72:2d:2a:ec", "0000:04:00.0", None, "eth0")
        cur_state = [cur_eth0]

        ts = rename_logic([srule_eth0],
                          deepcopy(cur_state),
                          [],
                          [])

        self.assertTrue(len(ts) == 0)

    def test_1drule_1eth_already_complete(self):
        """
        One recognised nic, and a dynamic rule for that nic.  Expecting no
        transactions at all.
        """

        cur_eth0 = MACPCI("00:13:72:2d:2a:ec", "0000:04:00.0", "eth0")
        drule_eth0 = MACPCI("00:13:72:2d:2a:ec", "0000:04:00.0", None, "eth0")
        cur_state = [cur_eth0]

        ts = rename_logic([],
                          deepcopy(cur_state),
                          [drule_eth0],
                          [])

        self.assertTrue(len(ts) == 0)

class TestUseCases(unittest.TestCase):

    def setUp(self):
        self.siobuff = StringIO()
        openLog(self.siobuff, logging.NOTSET)

    def tearDown(self):

        closeLogs()
        self.siobuff.close()

    def debug_state(self, ts):
        print("", file=sys.stderr)
        print(self.siobuff.getvalue(), file=sys.stderr)
        print("", file=sys.stderr)
        if len(ts):
            print("Transactions:", file=sys.stderr)
            for (s,d) in ts:
                print("'%s' -> '%s'" % (s, d), file=sys.stderr)
        else:
            print("No transactions", file=sys.stderr)
        print("", file=sys.stderr)

    def test_usecase1(self):
        """
        No changes from last boot.  No transactions and all nics
        retain their same name
        """
        cur_eth0 = MACPCI("01:23:45:67:89:01", "0000:01:00.0", "eth0")
        cur_eth1 = MACPCI("11:23:45:67:89:01", "0000:02:00.0", "eth1")
        cur_eth2 = MACPCI("21:23:45:67:89:01", "0000:03:00.0", "eth2")
        cur_eth3 = MACPCI("31:23:45:67:89:01", "0000:04:00.0", "eth3")
        cur_eth4 = MACPCI("41:23:45:67:89:01", "0000:05:00.0", "eth4")
        cur_state = [cur_eth0, cur_eth1, cur_eth2, cur_eth3, cur_eth4]

        last_eth0 = MACPCI("01:23:45:67:89:01", "0000:01:00.0", None, "eth0")
        last_eth1 = MACPCI("11:23:45:67:89:01", "0000:02:00.0", None, "eth1")
        last_eth2 = MACPCI("21:23:45:67:89:01", "0000:03:00.0", None, "eth2")
        last_eth3 = MACPCI("31:23:45:67:89:01", "0000:04:00.0", None, "eth3")
        last_eth4 = MACPCI("41:23:45:67:89:01", "0000:05:00.0", None, "eth4")
        last_state = [last_eth0, last_eth1, last_eth2, last_eth3, last_eth4]

        ts = rename([], cur_state, last_state, [])

        self.assertTrue(len(ts) == 0)

        for eth in cur_state:
            self.assertTrue(eth.kname == eth.tname)

    def test_usecase5(self):
        """
        Brand new hardware.  (Use case based upon plugging the hard drive from
        a broken server into a new identical one).
        """
        cur_eth0 = MACPCI("02:23:45:67:89:01", "0000:01:00.0", "side-1-eth0")
        cur_eth1 = MACPCI("12:23:45:67:89:01", "0000:02:00.0", "side-34-eth1")
        cur_eth2 = MACPCI("22:23:45:67:89:01", "0000:03:00.0", "side-71-eth2")
        cur_eth3 = MACPCI("32:23:45:67:89:01", "0000:04:00.0", "side-3012-eth3")
        cur_eth4 = MACPCI("42:23:45:67:89:01", "0000:05:00.0", "side-4332-eth4")
        cur_state = [cur_eth0, cur_eth1, cur_eth2, cur_eth3, cur_eth4]

        last_eth0 = MACPCI("01:23:45:67:89:01", "0000:01:00.0", None, "eth0")
        last_eth1 = MACPCI("11:23:45:67:89:01", "0000:02:00.0", None, "eth1")
        last_eth2 = MACPCI("21:23:45:67:89:01", "0000:03:00.0", None, "eth2")
        last_eth3 = MACPCI("31:23:45:67:89:01", "0000:04:00.0", None, "eth3")
        last_eth4 = MACPCI("41:23:45:67:89:01", "0000:05:00.0", None, "eth4")
        last_state = [last_eth0, last_eth1, last_eth2, last_eth3, last_eth4]

        ts = rename([], deepcopy(cur_state), last_state, [])

        self.assertTrue(len(ts) == 5)
        apply_transactions(cur_state, ts)

        for cur, last in zip(cur_state, last_state):
            self.assertTrue(cur.tname == last.tname)

    def test_CA_94279(self):
        """
        CA-94279 occurred because the logic did no honor the order parameter
        from biosdevname if it was the only deciding factor.  (It appears rare
        for the embedded network cards to have a greater PCI sbdf than the non-
        embedded cards)

        Check that in the order is honoured in the case where it is the only
        deciding factor.
        """

        cur_eth0 = MACPCI("00:1b:21:aa:ef:f0", "0000:03:00.0", "side-1-eth0", order=2)
        cur_eth1 = MACPCI("00:1b:21:aa:ef:f1", "0000:03:00.1", "side-2-eth1", order=3)
        cur_eth2 = MACPCI("00:1b:21:aa:ef:f4", "0000:04:00.0", "side-3-eth2", order=4)
        cur_eth3 = MACPCI("00:1b:21:aa:ef:f5", "0000:04:00.1", "side-4-eth3", order=5)
        cur_eth4 = MACPCI("60:eb:69:ed:9a:16", "0000:06:00.0", "side-5-eth4", order=0)
        cur_eth5 = MACPCI("60:eb:69:ed:9a:17", "0000:06:00.1", "side-6-eth5", order=1)
        cur_state = [ cur_eth0, cur_eth1, cur_eth2, cur_eth3, cur_eth4, cur_eth5 ]

        ts = rename([], deepcopy(cur_state), [], [])
        apply_transactions(cur_state, ts)

        expected_names = [ "eth2", "eth3", "eth4", "eth5", "eth0", "eth1" ]

        for cur, exp in zip(cur_state, expected_names):
            self.assertEqual(cur.tname, exp)

    def test_rshp_new_hardware(self):
        """
        Brand new hardware - including duplicate PCI ID.  (Use case based upon
        plugging the hard drive from a broken server into a new identical one,
        for the Rackspace HP blades with Mellanox cards with two eths per
        function).
        """
        cur_eth0 = MACPCI("02:23:45:67:89:01", "0000:01:00.0", "side-1-eth0")
        cur_eth1 = MACPCI("12:23:45:67:89:01", "0000:02:00.0", "side-34-eth1")
        cur_eth2 = MACPCI("22:23:45:67:89:01", "0000:03:00.0", "side-71-eth2")
        # Devices with the same PCI ID are assumed to differ by 1 in the MAC
        cur_eth3 = MACPCI("32:23:45:67:89:01", "0000:04:00.0", "side-3012-eth3")
        cur_eth4 = MACPCI("32:23:45:67:89:02", "0000:04:00.0", "side-4332-eth4")
        cur_state = [cur_eth0, cur_eth1, cur_eth2, cur_eth3, cur_eth4]

        last_eth0 = MACPCI("01:23:45:67:89:01", "0000:01:00.0", None, "eth0")
        last_eth1 = MACPCI("11:23:45:67:89:01", "0000:02:00.0", None, "eth1")
        last_eth2 = MACPCI("21:23:45:67:89:01", "0000:03:00.0", None, "eth2")
        # Devices with the same PCI ID are assumed to differ by 1 in the MAC
        # Make eth3 have a MAC higher than eth4 to ensure that we order the new NICs correctly
        last_eth3 = MACPCI("31:23:45:67:89:02", "0000:04:00.0", None, "eth3")
        last_eth4 = MACPCI("31:23:45:67:89:01", "0000:04:00.0", None, "eth4")
        last_state = [last_eth0, last_eth1, last_eth2, last_eth4, last_eth3]

        # Reverse order of input to ensure logic copes correctly
        ts = rename([], deepcopy(cur_state[::-1]), last_state, [])

        self.assertTrue(len(ts) == 5)
        apply_transactions(cur_state, ts)

        for cur, last in zip(cur_state, last_state):
            self.assertEqual(cur.tname, last.tname)

    def test_bad_biosdevname_order(self):
        """
        Brand new hardware - including multi-nic functions and incorrect biosdevname ordering
        """

        # Devices with the same PCI ID are assumed to differ by 1 in the MAC
        # Interlace two multi-nic functions, and have single-nic functions scattered around
        cur_state = []
        cur_state.append(MACPCI("00:00:00:00:00:01", "0000:01:00.0", order=0, kname="side-0-eth0"))

        cur_state.append(MACPCI("00:00:44:00:01:01", "0000:02:00.0", order=2, kname="side-0-eth2"))
        cur_state.append(MACPCI("00:00:44:00:01:02", "0000:02:00.0", order=6, kname="side-0-eth6"))
        cur_state.append(MACPCI("00:00:44:00:01:03", "0000:02:00.0", order=1, kname="side-0-eth1"))

        cur_state.append(MACPCI("00:00:00:00:02:01", "0000:03:00.0", order=4, kname="side-0-eth4"))

        # Second set of multi-nic functions has a lower MAC address than the first to make sure
        # orders aren't mixed between multi-nic functions
        cur_state.append(MACPCI("00:00:22:00:03:01", "0000:04:00.0", order=7, kname="side-0-eth5"))
        cur_state.append(MACPCI("00:00:22:00:03:02", "0000:04:00.0", order=3, kname="side-0-eth3"))
        cur_state.append(MACPCI("00:00:22:00:03:03", "0000:04:00.0", order=5, kname="side-0-eth7"))

        cur_state.append(MACPCI("00:00:00:00:04:01", "0000:05:00.0", order=8, kname="side-0-eth8"))

        expected_order = []
        expected_order.append(("eth0", "00:00:00:00:00:01")) # non-MNF; biosdevname order
        expected_order.append(("eth1", "00:00:44:00:01:01")) # MNF 1, ordered by MAC
        expected_order.append(("eth2", "00:00:44:00:01:02")) # MNF 1, ordered by MAC
        expected_order.append(("eth3", "00:00:22:00:03:01")) # MNF 2, ordered by MAC
        expected_order.append(("eth4", "00:00:00:00:02:01")) # non-MNF; biosdevname order
        expected_order.append(("eth5", "00:00:22:00:03:02")) # MNF 2, ordered by MAC
        expected_order.append(("eth6", "00:00:44:00:01:03")) # MNF 1, ordered by MAC
        expected_order.append(("eth7", "00:00:22:00:03:03")) # MNF 2, ordered by MAC
        expected_order.append(("eth8", "00:00:00:00:04:01")) # non-MNF; biosdevname order

        # Reverse order of input to ensure logic copes correctly
        ts = rename([], deepcopy(cur_state[::-1]), [], [])

        self.assertEqual(len(ts), 9)

        apply_transactions(cur_state, ts)
        cur_state.sort(key=lambda x: x.tname)

        for cur, expected in zip(cur_state, expected_order):
            self.assertEqual(cur.tname, expected[0])
            self.assertEqual(cur.mac, expected[1])

    def test_ibft_new_hardware(self):
        """
        Brand new hardware.  (Use case based upon plugging the hard drive from
        a broken server into a new identical one).
        """
        cur_eth0 = MACPCI("02:23:45:67:89:01", "0000:01:00.0", "side-1-eth0")
        cur_eth1 = MACPCI("12:23:45:67:89:01", "0000:02:00.0", "side-34-eth1")
        cur_eth2 = MACPCI("22:23:45:67:89:01", "0000:03:00.0", "ibft0")
        cur_eth3 = MACPCI("32:23:45:67:89:01", "0000:04:00.0", "side-3012-eth3")
        cur_eth4 = MACPCI("42:23:45:67:89:01", "0000:05:00.0", "side-4332-eth4")
        cur_state = [cur_eth0, cur_eth1, cur_eth2, cur_eth3, cur_eth4]

        ts = rename([], deepcopy(cur_state), [], [])

        self.assertEqual(len(ts), 4)
        apply_transactions(cur_state, ts)
        self.assertEqual(cur_eth0.tname, "eth0")
        self.assertEqual(cur_eth1.tname, "eth1")
        self.assertEqual(cur_eth3.tname, "eth2")
        self.assertEqual(cur_eth4.tname, "eth3")

    def test_ibft_no_change(self):
        """
        No changes from last boot.  No transactions and all nics
        retain their same name
        """
        cur_eth0 = MACPCI("01:23:45:67:89:01", "0000:01:00.0", "eth0")
        cur_eth1 = MACPCI("11:23:45:67:89:01", "0000:02:00.0", "eth1")
        cur_eth2 = MACPCI("21:23:45:67:89:01", "0000:03:00.0", "ibft0")
        cur_eth3 = MACPCI("31:23:45:67:89:01", "0000:04:00.0", "eth2")
        cur_eth4 = MACPCI("41:23:45:67:89:01", "0000:05:00.0", "eth3")
        cur_state = [cur_eth0, cur_eth1, cur_eth2, cur_eth3, cur_eth4]

        last_eth0 = MACPCI("01:23:45:67:89:01", "0000:01:00.0", None, "eth0")
        last_eth1 = MACPCI("11:23:45:67:89:01", "0000:02:00.0", None, "eth1")
        last_eth3 = MACPCI("31:23:45:67:89:01", "0000:04:00.0", None, "eth2")
        last_eth4 = MACPCI("41:23:45:67:89:01", "0000:05:00.0", None, "eth3")
        last_state = [last_eth0, last_eth1, last_eth3, last_eth4]

        ts = rename([], cur_state, last_state, [])

        self.assertEqual(len(ts), 0)

        for eth in cur_state:
            # Skip the iBFT NIC since it doesn't get a tname and is completely
            # ignored.
            if eth.kname != "ibft0":
                self.assertEqual(eth.kname, eth.tname)

    def test_ibft_nic_to_ibft(self):
        """
        Convert a NIC to iBFT.  Since iBFT NICs are ignored, no transactions
        are expected.
        """
        cur_eth0 = MACPCI("01:23:45:67:89:01", "0000:01:00.0", "eth0")
        cur_eth1 = MACPCI("11:23:45:67:89:01", "0000:02:00.0", "eth1")
        cur_eth2 = MACPCI("21:23:45:67:89:01", "0000:03:00.0", "ibft0")
        cur_eth3 = MACPCI("31:23:45:67:89:01", "0000:04:00.0", "eth3")
        cur_eth4 = MACPCI("41:23:45:67:89:01", "0000:05:00.0", "eth4")
        cur_state = [cur_eth0, cur_eth1, cur_eth2, cur_eth3, cur_eth4]

        last_eth0 = MACPCI("01:23:45:67:89:01", "0000:01:00.0", None, "eth0")
        last_eth1 = MACPCI("11:23:45:67:89:01", "0000:02:00.0", None, "eth1")
        last_eth2 = MACPCI("21:23:45:67:89:01", "0000:03:00.0", None, "eth2")
        last_eth3 = MACPCI("31:23:45:67:89:01", "0000:04:00.0", None, "eth3")
        last_eth4 = MACPCI("41:23:45:67:89:01", "0000:05:00.0", None, "eth4")
        last_state = [last_eth0, last_eth1, last_eth2, last_eth3, last_eth4]

        ts = rename([], cur_state, last_state, [])

        self.assertEqual(len(ts), 0)

        for eth in cur_state:
            # Skip the iBFT NIC since it doesn't get a tname and is completely
            # ignored.
            if eth.kname != "ibft0":
                self.assertEqual(eth.kname, eth.tname)


class TestInputSanitisation(unittest.TestCase):
    # pylint: disable=no-member

    def setUp(self):
        """
        Set up a lot of MACPCI objects.

        This reflection magic creates many self.cXXX objects where XXX
        represents the indices of mac, pci and eth names.
        e.g. self.c123 means the 1st mac, 2nd pci and 3rd eth
             self.c221 means the 2nd mac, 2nd pci and 1st eth

        In addition, set up equivalent self.sXXX objects which have a kname
        set to None and a tname set to the 'eth'
        """

        self.siobuff = StringIO()
        openLog(self.siobuff)


        macs = ["ab:cd:ef:01:23:45", "02:46:8A:CE:15:79", "ab:ba:ab:ba:ab:ba"]
        pcis = ["0000:00:00.1", "0000:00:00.2", "0001:00:00.2"]
        eths = ["eth1", "eth2", "eth3"]

        for (mn, m) in enumerate(macs):
            for (pn, p) in enumerate(pcis):
                for (en, e) in enumerate(eths):
                    setattr(self, "c%d%d%d" % (mn+1, pn+1, en+1),
                            MACPCI(m, p, e, None))
                    setattr(self, "s%d%d%d" % (mn+1, pn+1, en+1),
                            MACPCI(m, p, None, e))

    def tearDown(self):

        closeLogs()
        self.siobuff.close()


    def test_srule_eth_unaliased(self):
        rename([self.s111], [], [], [])

    def test_srule_eth_alias(self):
        """
        Ensure that no static rules attempt to alias the same eth name
        """

        srule_inputs = [ [self.s111, self.s221],
                         [self.s111, self.s221, self.s331],
                         [self.s111, self.s222, self.s331],
                         [self.s112, self.s222, self.s331] ]

        for i in srule_inputs:
            with self.assertRaises(StaticRuleError):
                rename(i, [], [], [])

    def test_srule_mac_alias(self):
        """
        Ensure that no static rules attempt to alias the same mac address
        """

        srule_inputs = [ [self.s111, self.s122],
                         [self.s111, self.s122, self.s133],
                         [self.s111, self.s222, self.s133],
                         [self.s211, self.s222, self.s133] ]

        for i in srule_inputs:
            with self.assertRaises(StaticRuleError):
                rename(i, [], [], [])

    def test_curstate_eth_alias(self):
        """
        Ensure that no current state entries attempt to alias the same eth name
        """

        curstate_inputs = [ [self.c111, self.c221],
                            [self.c111, self.c221, self.c331],
                            [self.c111, self.c222, self.c331],
                            [self.c112, self.c222, self.c331] ]

        for i in curstate_inputs:
            with self.assertRaises(CurrentStateError):
                rename([], i, [], [])

    def test_curstate_mac_alias(self):
        """
        Ensure that no current state attempt to alias the same mac address
        """

        curstate_inputs = [ [self.c111, self.c122],
                            [self.c111, self.c122, self.c133],
                            [self.c111, self.c222, self.c133],
                            [self.c211, self.c222, self.c133] ]

        for i in curstate_inputs:
            with self.assertRaises(CurrentStateError):
                rename([], i, [], [])

    def test_laststate_input(self):
        """
        Ensure that last state only accepts rules in the form
          (xx:xx.x,xx:xx:xx:xx:xx:xx)->eth##
        """

        with self.assertRaises(LastStateError):
            rename([], [], [self.c123], [])

        rename([], [], [self.s123], [])

    def test_oldstate_input(self):
        """
        Ensure that old state only accepts rules in the form
          (xx:xx.x,xx:xx:xx:xx:xx:xx)->eth##
        """

        with self.assertRaises(OldStateError):
            rename([], [], [], [self.c123])

        rename([], [], [], [self.s123])
