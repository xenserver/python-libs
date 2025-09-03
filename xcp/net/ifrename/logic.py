# Copyright (c) 2013, Citrix Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Interface Rename logic

Provides the 'rename' function which takes 4 lists of state and returns a list
of name transactions to rename network interfaces.

[in]  static_rules - Static rules provided by the user, taking absolute priority
        list of MACPCI objects in form (mac, pci)->ethXX
[in]  cur_state - Current state of network cards on the machine (pre rename)
        list of MACPCI objects in form ethXXX|side-XXX-ethXX->(mac, pci)
[in]  last_state - Last boot state (post rename) of network cards on the machine
        list of MACPCI objects in form (mac, pci)->ethXX
[in]  old_state - Any older nics which have disappeared in the meantime
        list of MACPCI objects in form (mac, pci)->ethXX

[out] transactions
        list of string tuples as source and destination names for "ip link set
        name"

Abbreviations used in this file:
    kname: The kernel name of the network interface (the original name assigned by the kernel).
    tname: The temporary name of the interface, used while renaming interfaces to avoid name conflicts.
"""

from __future__ import unicode_literals

__version__ = "1.0.0"
__author__  = "Andrew Cooper"

import re

from xcp.logger import LOG
from xcp.net.ifrename import VALID_ETH_NAME, util
from xcp.net.ifrename.macpci import MACPCI

VALID_CUR_STATE_KNAME = re.compile(r"^(?:eth[\d]+|side-[\d]+-eth[\d]+)$")
VALID_IBFT_NAME = re.compile(r"^ibft([\d])+$")


class StaticRuleError(RuntimeError):
    """Error with static rules"""
class CurrentStateError(RuntimeError):
    """Error with current state information"""
class LastStateError(RuntimeError):
    """Error with last state information"""
class OldStateError(RuntimeError):
    """Error with old state information"""
class LogicError(RuntimeError):
    """Logical Error.  Needs fixing"""


def __rename_nic(nic, name, transactions, cur_state):
    """
    Rename a specified nic to name.
    It checkes in possibly_aliased for nics which currently have name, and
    renames them sideways.
    The caller should ensure that no nics in cur_state have already been renamed
    to name, and that name is a valid nic name
    """

    # Assert that name is valid
    assert VALID_ETH_NAME.match(name) is not None
    # Assert that name is not already taken in the current state
    assert name not in (x.tname for x in cur_state)

    # Given the previous assert, only un-renamed nics in the current state can
    # possibly alias the new name
    aliased = util.get_nic_with_kname(
        (x for x in cur_state if x.tname is None), name)

    if aliased is None:
        # Using this rule will not alias another currently present NIC
        LOG.debug("Renaming unaliased nic '%s' to '%s'" % (nic, name))
        nic.tname = name
        transactions.append((nic.kname, name))

    elif aliased == nic and aliased.kname == nic.kname:
        # The nic is already named correctly.  Just update tname
        LOG.debug("Nic '%s' is already named correctly" % (nic,))
        nic.tname = nic.kname

    else:
        # Another nic is in the way for applying the rule.  Move it sideways

        # Old comment from 2012: given new assertions, will this ever be necessary?
        if aliased.kname[:5] == "side-":
            aliased_eth = aliased.kname.split('-')[2]
        else:
            aliased_eth = aliased.kname

        tempname = util.get_new_temp_name(cur_state, aliased_eth)
        LOG.debug("Nic '%s' aliases rename of '%s' to '%s'"
                  % (aliased, nic, name))

        # Rename aliased nic sideways
        LOG.debug("Renaming aliased nic to '%s'" % (tempname,))
        transactions.append((aliased.kname, tempname))
        aliased.kname = tempname

        # And then rename the original nic
        LOG.debug("Renaming original nic to '%s'" % (name,))
        nic.tname = name
        transactions.append((nic.kname, name))


def rename_logic(static_rules, cur_state, last_state, old_state):
    """
    Core logic of renaming the current state based on the rules and past state.

    This function assumes all inputs have been suitably sanitised.

    Parameters
    ----------
    static_rules : list[MACPCI]
        List of MACPCI objects representing rules
    cur_state : list[MACPCI]
        List of MACPCI objects representing the current state
    last_state : list[MACPCI]
        List of MACPCI objects representing the last boot state
    old_state : list[MACPCI]
        List of MACPCI objects representing the old state

    Returns
    -------
    list
        List of tuples representing name transactions.

    Raises
    ------
    AssertionError
        If the current state contains invalid entries.
    """

    transactions = []

    if not len(cur_state):
        # If there are no nics present on the system, no renaming to perform
        return transactions

    # Certain drivers advertise multiple eth devices for the same PCI function
    # To avoid breaking the logic later, we need to know which PCI functions
    # have multiple eths.  As this is a per-driver effect, calculate it only
    # from the current state and not any saved state.
    multinic_functions = set()
    pci_functions = set()
    for nic in cur_state:
        if nic.pci in pci_functions:
            multinic_functions.add(nic.pci)
        else:
            pci_functions.add(nic.pci)
    if len(multinic_functions):
        LOG.debug("Detected the following PCI functions with multiple nics\n%s"
                  % (util.niceformat(multinic_functions),))

    # 1st pass.  Force current state into line according to the static rules
    for rule in static_rules:
        LOG.debug("Considering static rule '%s'" % (rule,))

        try:
            nic = cur_state[cur_state.index(rule)]
        except ValueError:
            LOG.debug("Static rule does not reference a current nic")
            continue

        __rename_nic(nic, rule.tname, transactions, cur_state)

    LOG.debug("Finished static rules. Transactions are \n%s\n"
              "Current State is \n%s" % (util.niceformat(transactions),
                                         util.niceformat(cur_state)))

    # 2nd pass. This logic should cover nics referenced by last or old state
    for nic in filter(util.needs_renaming, cur_state):
        LOG.info("Considering '%s'" % (nic,))

        # Did this nic appear in the same pci location as last boot?
        try:
            lastnic = last_state[last_state.index(nic)]
        except ValueError:
            # No it did not appear in the same location as before
            pass
        else:
            can_rename = util.tname_free(cur_state, lastnic.tname)

            # Warn if UDEV failed to rename the nic.  Either there is a logical
            # bug somewhere, or the user is messing around with our files.
            if VALID_CUR_STATE_KNAME.match(nic.kname) is None:
                LOG.warning("nic '%s' was not renamed by udev." % (nic,))

            # If the correct target name is free, attempt to rename to it.
            if can_rename:
                LOG.info("nic '%s' in the same location as before. "
                         "Renaming to %s" % (nic, lastnic.tname))
                __rename_nic(nic, lastnic.tname, transactions, cur_state)
            else:
                # If the target name is already taken, warn about it
                LOG.warning("nic '%s' aliased from its last boot location. "
                            "Defering renaming and treating as new"
                            % (nic,))
            continue


        # if we saw this nic last time but its pci location is different, we
        # have just moved hardware on the bus so give it the old name
        lastnic = util.get_nic_with_mac(last_state, nic.mac)
        LOG.debug("nic_with_mac(last_state, %s) = %s" % (nic.mac, lastnic))
        if lastnic:
            LOG.info("nic '%s' moved on the pci bus from '%s'"
                     % (nic, lastnic))
            __rename_nic(nic, lastnic.tname, transactions, cur_state)
            continue

        # else this mac was not seen last boot. Is it on a multinic function?
        if nic.pci in multinic_functions:
            # if it is on a multinic_function, consider it brand new and rename
            # later
            LOG.info("nic '%s' is on a multinic pci function. Considering it "
                     "new and renaming later" % (nic,))
            continue

        # this nic is not on a multinic function.  Has it displaced another nic?
        lastnic = util.get_nic_with_pci(last_state+old_state, nic.pci)
        LOG.debug("nic_with_pci(last_state+old_state, %s) = %s"
                  % (nic.mac, lastnic))
        if lastnic:
            # This nic is in the place of an older nic.  Is that older nic still
            # present elsewhere in the system?
            if util.get_nic_with_mac(cur_state, lastnic.mac) is not None:
                # Yes - the displaced nic is still preset.  Therefore, that nic
                # has moved and this current nic is new.
                LOG.info("nic '%s' displaced older nic '%s' which is still "
                         "present.  Considering this nic new" % (nic, lastnic))
            else:
                # No - the displaced nic is no longer present so consider it
                # replaced
                LOG.info("nic '%s' has replaced older nic '%s'"
                         % (nic, lastnic))
                __rename_nic(nic, lastnic.tname, transactions, cur_state)
            continue

        # have we ever seen this nic before?
        lastnic = util.get_nic_with_mac(old_state, nic.mac)
        LOG.debug("nic_with_mac(old_state, %s) = %s" % (nic.mac, lastnic))
        if lastnic:
            # Yes - this nic was once present but not present last boot
            # Is its old name still availble?
            if util.tname_free(cur_state, lastnic.tname):
                # Old name is available - give it its old name back
                LOG.info("old nic '%s' returned and its name is free"
                         % (nic,))
                __rename_nic(nic, lastnic.tname, transactions, cur_state)
            else:
                LOG.info("old nic '%s' returned but its name is taken. "
                         "Treating it as new" % (nic,))
            continue

        LOG.info("nic '%s' seems brand new.  Defering until later for renaming"
                 % (nic,))


    LOG.debug("Finished dynamic rules. Transactions are \n%s\n"
              "Current State is \n%s" % (util.niceformat(transactions),
                                         util.niceformat(cur_state)))

    # 3rd pass.  This pass ensures that replaced multi-nic functions
    # are ordered the same as a the previous state, relative to MACs.
    #
    # New multi-nic functions get ordered below.
    if len(multinic_functions):

        for fn in multinic_functions:
            lastnics = util.get_nics_with_pci(last_state + old_state, fn)
            newnics  = util.get_nics_with_pci(cur_state, fn)

            # Check that the function still has the same number of nics
            if len(lastnics) != len(newnics):
                LOG.warning(
                    "multi-nic function %s had %d nics but now has %d.  "
                    "Defering all until later for renaming",
                    fn, len(lastnics), len(newnics))
                continue

            # Check that all nics are still pending a rename
            if False in (util.needs_renaming(n) for n in newnics):
                LOG.info("Some of %s's nics have already been renamed.  "
                         "Defering the rest until later for renaming"
                         % (fn, ))
                continue

            # Check that all expected target names are free
            if False in (util.tname_free(cur_state, n.tname) for n in lastnics):
                LOG.info("Some of %s's nics target names already used.  "
                         "Defering the rest until later for renaming"
                         % (fn, ))
                continue

            # Assume the MACs are ordered reliably.  They are typically adjacent
            lastnics.sort(key = lambda n: n.mac.integer)
            newnics.sort(key = lambda n: n.mac.integer)

            for new, old in zip(newnics, lastnics):
                __rename_nic(new, old.tname, transactions, cur_state)

        LOG.debug("Finished multi-nic logic.  Transactions are \n%s\n"
                  "Current State is \n%s" % (util.niceformat(transactions),
                                             util.niceformat(cur_state)))

    # There may be some new multinic functions.  We can't trust biosdevname's
    # order for these NICs, so for each NIC collect the reported "order" <n>
    # (derived directly from eth<n>) and sort them according to the MACs
    if len(multinic_functions):
        LOG.debug("New multi-nic logic - attempting to re-order")
        for fn in multinic_functions:
            newnics = util.get_nics_with_pci((x for x in cur_state if util.needs_renaming(x)), fn)
            orders = sorted(x.order for x in newnics)
            newnics.sort(key = lambda n: n.mac.integer)
            for nic, neworder in zip(newnics, orders):
                LOG.debug("NIC '%s' getting new order '%s'" % (nic, neworder))
                nic.order = neworder

    # For completely new network cards which we have never seen before, work out
    # a safe new number to assign it
    ethnumbers = sorted(
        int(x[3:])
        for x in (x.tname or x.kname for x in static_rules + cur_state + last_state)
        if VALID_ETH_NAME.match(x) is not None)
    if len(ethnumbers):
        nextethnum = ethnumbers[-1]+1
    else:
        nextethnum = 0

    # 4th pass. This should only affect brand new network cards unreferenced
    # by previous state.  Prefer the order (e.g. from biosdevname), given
    # no other objections.
    for nic in sorted(filter(util.needs_renaming, cur_state),
                      key=lambda x: x.order):
        LOG.info("Renaming brand new nic '%s'" % (nic,))

        if (VALID_ETH_NAME.match(nic.kname) is not None and
                nic.kname not in (x.tname for x in cur_state)):
            # User has been messing around with state files but not the udev
            # rules.  If the eth name is still free, give it

            nic.tname = nic.kname
            # No transaction needed
            continue

        newname = "eth%d" % (nextethnum, )
        nextethnum += 1
        __rename_nic(nic, newname, transactions, cur_state)


    LOG.debug("Finished all logic. Transactions are \n%s\n"
              "Current State is \n%s" % (util.niceformat(transactions),
                                         util.niceformat(cur_state)))
    return transactions

def rename(static_rules, cur_state, last_state, old_state):
    """
    Rename current state based on the rules and past state.

    This function:
    - Sanitises the input
    - Delegates the renaming logic to rename_logic()

    Parameters
    ----------
    static_rules : list[MACPCI]
        List of MACPCI objects representing rules
    cur_state : list[MACPCI]
        List of MACPCI objects representing the current state
    last_state : list[MACPCI]
        List of MACPCI objects representing the last boot state
    old_state : list[MACPCI]
        List of MACPCI objects representing the old state

    Returns
    -------
    list
        List of tuples of name changes required

    Raises
    ------
    StaticRuleError
        Raised if any of the following conditions are met:
        - A static rule has a kernel name.
        - A static rule has a tname not starting with 'eth'.
        - Duplicate eth names are present in static rules.
        - Duplicate MAC addresses are present in static rules.
    CurrentStateError
        If the current state contains invalid entries.
    LastStateError
        If the last state contains invalid entries.
    TypeError
        If any of the input lists contain objects that are not MACPCI instances.
    """

    if len(static_rules):

        # Verify types and properties of the list
        for e in static_rules:
            # Verify type
            if not isinstance(e, MACPCI):
                raise TypeError("Expected List of MACPCI objects")

            # Verify kname is None
            if e.kname is not None:
                raise StaticRuleError("Expected static rule kname to be None")

            # Verify tname points to 'eth<foo>'
            if not e.tname.startswith("eth"):
                raise StaticRuleError("Static rule '%s' expected to name to "
                                      "'eth<num>'" % (e, ))

        # Verify no two static rules refer to the same eth name
        _ = frozenset(x.tname for x in static_rules)
        if len(_) != len(static_rules):
            raise StaticRuleError("Some static rules alias the same "
                                  "eth name")

        # Verify no two static rules refer to the same mac address
        _ = frozenset(x.mac for x in static_rules)
        if len(_) != len(static_rules):
            raise StaticRuleError("Some static rules alias the same MAC "
                                  "address")

    if len(cur_state):
        # Filter out iBFT NICs
        cur_state = [x for x in cur_state if VALID_IBFT_NAME.match(x.kname) is None]

        # Verify types and properties of the list
        for e in cur_state:
            if not isinstance(e, MACPCI):
                raise TypeError("Expected List of MACPCI objects")

            # Verify tname is None
            if e.tname is not None:
                raise CurrentStateError("Expected current state tname to be "
                                        " None")

            # Verify kname is 'eth<foo>' or 'side-<num>-eth<num>'
            if VALID_CUR_STATE_KNAME.match(e.kname) is None:
                raise StaticRuleError("Current state '%s' expected to name to "
                                      "'eth<num>' or 'side-<num>-eth<num>'"
                                      % (e, ))


        # Verify no two entries of current state refer to the same eth name
        _ = frozenset(x.kname for x in cur_state)
        if len(_) != len(cur_state):
            raise CurrentStateError("Some entries of current state alias the "
                                    "same eth name")

        # Verify no two entries of current state refer to the same mac address
        _ = frozenset(x.mac for x in cur_state)
        if len(_) != len(cur_state):
            raise CurrentStateError("Some entries of current state alias the "
                                    "same MAC address")

    if len(last_state):

        # Verify types in the list
        for e in last_state:
            if not isinstance(e, MACPCI):
                raise TypeError("Expected List of MACPCI objects")

            # Verify kname is None
            if e.kname is not None:
                raise LastStateError("Expected last state kname to be None")

            # Verify kname is valid
            if VALID_ETH_NAME.match(e.tname) is None:
                raise LastStateError("Last state '%s' target name is invalid"
                                     % (e, ))


        # Verify no two entries of last state refer to the same eth name
        _ = frozenset(x.tname for x in last_state)
        if len(_) != len(last_state):
            raise LastStateError("Some entries of last state alias the "
                                 "same eth name")

        # Verify no two entries of last state refer to the same mac address
        _ = frozenset(x.mac for x in last_state)
        if len(_) != len(last_state):
            raise LastStateError("Some entries of last state alias the "
                                 "same MAC address")

    if len(old_state):

        # Verify types in the list
        for e in old_state:
            if not isinstance(e, MACPCI):
                raise TypeError("Expected List of MACPCI objects")

            # Verify kname is None
            if e.kname is not None:
                raise OldStateError("Expected old state kname to be None")

            # Verify tname points to 'eth<foo>'
            if not e.tname.startswith("eth"):
                raise OldStateError("Old state '%s' expected tname to "
                                      "'eth<num>'" % (e, ))


    return rename_logic(static_rules, cur_state, last_state, old_state)
