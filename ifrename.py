#!/usr/bin/env python
# Copyright (c) 2012 Citrix Systems, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; version 2.1 only. with the special
# exception on linking described in file LICENSE.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

"""
Interface Rename logic

Provides the 'rename' function which takes 4 lists of state and returns a list
of name transactions to rename network interfaces.

[in]  static_rules - Static rules provided by the user, taking absolute priority
        list of MACPCIName objects in form (mac, pci)->ethXX
[in]  cur_state - Current state of network cards on the machine (pre rename)
        list of MACPCIName objects in form ethXXX|side-XXX-ethXX->(mac, pci)
[in]  last_state - Last boot state (post rename) of network cards on the machine
        list of MACPCIName objects in form (mac, pci)->ethXX
[in]  old_state - Any older nics which have disappeared in the meantime
        list of MACPCIName objects in form (mac, pci)->ethXX

[out] transactions
        list of string tuples as source and destination names for "ip link set
        name"
"""

__version__ = "1.0"
__author__  = "Andrew Cooper"

from logger import LOG
import re, random, pprint

VALID_CUR_STATE_KNAME = re.compile("^(?:eth[\d]+|side-[\d]+-eth[\d]+)$")
VALID_ETH_NAME = re.compile("^eth([\d])+$")

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

class MACPCIName(object):

    def __init__(self, mac, pci, kname=None, tname=None, order=0):
        self.mac = mac.upper()
        self.pci = pci.upper()
        self.kname = kname
        self.tname = tname
        self.order = order

    def __str__(self):
        res = ""
        if self.kname:
            res += "%s->" % (self.kname,)
        res += "(%s,%s)" % (self.mac, self.pci)
        if self.tname:
            res += "->%s" % (self.tname,)
        return res

    def __repr__(self):
        return str(self)
        #return "<MACPCIName object '%s'>" % (self,)

    def __eq__(self, other):
        return ( self.mac == other.mac and
                 self.pci == other.pci )

    def __ne__(self, other):
        return ( self.mac != other.mac or
                 self.pci != other.pci )

    def __lt__(self, other):
        return self.order < other.order

def __niceformat(obj):
    """conditional pprint"""
    try:
        if len(obj) > 1:
            return pprint.pformat(obj, indent=2)
    except Exception:
        return str(obj)
    else:
        return str(obj)


def __get_nic_with_kname(nics, kname):
    """Search for nic with kname"""
    for nic in nics:
        if nic.kname == kname:
            return nic
    return None

def __tname_free(nics, name):
    """Check that name is not taken by any nics"""
    return name not in map(lambda x: x.tname, nics)

def __get_nic_with_mac(nics, mac):
    """Search for nic with mac"""
    for nic in nics:
        if nic.mac == mac:
            return nic
    return None

def __get_nic_with_pci(nics, pci):
    """Search for nic with pci"""
    for nic in nics:
        if nic.pci == pci:
            return nic
    return None

def __get_new_temp_name(nics, eth):
    """Generate a new temporary name"""
    names = ( [ x.kname for x in nics if x.kname ] +
              [ x.tname for x in nics if x.tname ] )
    while True:
        rn = random.randrange(1, 2**16-1)
        name = "side-%d-%s" % (rn, eth)
        if name not in names:
            return name

def __needs_renaming(nic):
    """Check whether a nic needs renaming or not"""
    if nic.tname and VALID_ETH_NAME.match(nic.tname) is not None:
        return False
    return True

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
    assert name not in map(lambda x: x.tname, cur_state)

    # Given the previous assert, only un-renamed nics in the current state can
    # possibly alias the new name
    aliased = __get_nic_with_kname(
        filter(lambda x: x.tname is None, cur_state), name)

    if aliased is None:
        # Using this rule will not alias another currently present NIC
        LOG.debug("Renaming unaliased nic '%s' to '%s'" % (nic, name))
        nic.tname = name
        transactions.append((nic.kname, name))
    else:
        # Another nic is in the way for applying the rule.  Move it sideways

        # TODO: given new assertions, will this ever be nessesary?
        if aliased.kname[:5] == "side-":
            aliased_eth = aliased.kname.split('-')[2]
        else:
            aliased_eth = aliased.kname

        tempname = __get_new_temp_name(cur_state, aliased_eth)
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


def rename_logic( static_rules,
                  cur_state,
                  last_state,
                  old_state ):
    """
    Core logic of renaming the current state based on the rules and past state.
    This function assumes all inputs have been suitably sanitised.
    @param static_rules
        List of MACPCIName objects representing rules
    @param cur_state
        List of MACPCIName objects representing the current state
    @param last_state
        List of MACPCIName objects representing the last boot state
    @param old_state
        List of MACPCIName objects representing the old state
    @returns List of tuples...
    @throws AssertionError (Should not be thrown, but better to know about logic
    errors if they occur)
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
            multinic_functions.update(nic.pci)
        else:
            pci_functions.update(nic.pci)
    if len(multinic_functions):
        LOG.debug("Detected the following PCI functions with multiple nics\n%s"
                  % (__niceformat(multinic_functions),))

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
              "Current State is \n%s" % (__niceformat(transactions),
                                         __niceformat(cur_state)))

    # 2nd pass. This logic should cover nics referenced by last or old state
    for nic in filter(__needs_renaming, cur_state):
        LOG.info("Considering '%s'" % (nic,))

        # Did this nic appear in the same pci location as last boot?
        try:
            lastnic = last_state[last_state.index(nic)]
        except ValueError:
            # No it did not appear in the same location as before
            pass
        else:
            can_rename = __tname_free(cur_state, lastnic.tname)

            # Warn if UDEV failed to rename the nic.  Either there is a logical
            # bug somewhere, or the user is messing around with our files.
            if VALID_ETH_NAME.match(nic.kname) is None:
                LOG.warning("nic '%s' in same location as last boot was not "
                            "renamed by udev." % (nic,))

            # Warn if UDEV did rename the nic, but not as per the last boot
            # information
            elif nic.kname != lastnic.tname:
                LOG.warning("nic '%s' in same location as last boot was "
                            "renamed by udev but to an unexpected name."
                            % (nic,))

            # It seems that UDEV is in order and it did successfully rename
            # the nic as instructed
            else:
                # If all is in order, and the nic currently has the same name
                # as it should end up having, fake a rename and make no
                # transactions for "ip link" to perform
                if can_rename:
                    LOG.info("nic '%s' in the same location as before. Keeping "
                             "it in the same location" % (nic,))
                    nic.tname = lastnic.tname
                    continue

            # If the correct target name is free, attempt to rename to it.
            if can_rename:
                LOG.info("nic '%s' in the same location as before but with a "
                         "wrong name.  Renaming to %s" % (nic, lastnic.tname))
                __rename_nic(nic, lastnic.tname, transactions, cur_state)
            else:
                # If the target name is already taken, warn about it
                LOG.warning("nic '%s' aliased from its last boot location. "
                            "Defering renaming and treating as new"
                            % (nic,))
            continue


        # if we saw this nic last time but its pci location is different, we
        # have just moved hardware on the bus so give it the old name
        lastnic = __get_nic_with_mac(last_state, nic.mac)
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
        lastnic = __get_nic_with_pci(last_state+old_state, nic.pci)
        LOG.debug("nic_with_pci(last_state+old_state, %s) = %s"
                  % (nic.mac, lastnic))
        if lastnic:
            # This nic is in the place of an older nic.  Is that older nic still
            # present elsewhere in the system?
            if __get_nic_with_mac(cur_state, lastnic.mac) is not None:
                # Yes - the displaced nic is still preset.  Therefore, that nic
                # has moved and this current nic is new.
                LOG.info("nic '%s' displaced older nic '%s' which is still "
                         "present.  Considering this nic new" % (nic, lastnic))
                continue
            else:
                # No - the displaced nic is no longer present so consider it
                # replaced
                LOG.info("nic '%s' has replaced older nic '%s'"
                         % (nic, lastnic))
                __rename_nic(nic, lastnic.tname, transactions, cur_state)
                continue

        # have we ever seen this nic before?
        lastnic = __get_nic_with_mac(old_state, nic.mac)
        LOG.debug("nic_with_mac(old_state, %s) = %s" % (nic.mac, lastnic))
        if lastnic:
            # Yes - this nic was once present but not present last boot
            # Is its old name still availble?
            if __tname_free(cur_state, lastnic.tname):
                # Old name is available - give it its old name back
                LOG.info("old nic '%s' returned and its name is free"
                         % (nic,))
                __rename_nic(nic, lastnic.tname, transactions, cur_state)
                continue
            else:
                LOG.info("old nic '%s' returned but its name is taken. "
                         "Treating it as new" % (nic,))
                continue

        LOG.info("nic '%s' seems brand new.  Defering until later for renaming"
                 % (nic,))


    LOG.debug("Finished dynamic rules. Transactions are \n%s\n"
              "Current State is \n%s" % (__niceformat(transactions),
                                         __niceformat(cur_state)))


    # For completely new network cards which we have never seen before, work out
    # a safe new number to assign it
    ethnumbers = sorted(
        map(lambda x: int(x[3:]),
            filter(lambda x: VALID_ETH_NAME.match(x) is not None,
                   map(lambda x: x.tname or x.kname,
                       static_rules + cur_state + last_state))))
    if len(ethnumbers):
        nextethnum = ethnumbers[-1]+1
    else:
        nextethnum = 0


    # 3rd pass. This should only affect brand new network cards unreferenced
    # by previous state
    for nic in filter(__needs_renaming, cur_state):
        LOG.info("Renaming brand new nic '%s'" % (nic,))

        if ( VALID_ETH_NAME.match(nic.kname) is not None and
             nic.kname not in map(lambda x: x.tname, cur_state) ):
            # User has been messing around with state files but not the udev
            # rules.  If the eth name is still free, give it

            nic.tname = nic.kname
            # No transaction needed
            continue

        newname = "eth%d" % (nextethnum, )
        nextethnum += 1
        __rename_nic(nic, newname, transactions, cur_state)


    LOG.debug("Finished all logic. Transactions are \n%s\n"
              "Current State is \n%s" % (__niceformat(transactions),
                                         __niceformat(cur_state)))
    return transactions

def rename( static_rules,
            cur_state,
            last_state,
            old_state ):
    """
    Rename current state based on the rules and past state.
    This function sanitises the input and delgates the renaming logic to
    __rename.
    @param static_rules
        List of MACPCIName objects representing rules
    @param cur_state
        List of MACPCIName objects representing the current state
    @param last_state
        List of MACPCIName objects representing the last boot state
    @param old_state
        List of MACPCIName objects representing the old state

    @throws StaticRuleError, CurrentStateError, LastStateError, TypeError

    @returns list of tuples of name changes requred
    """

    if len(static_rules):

        # Verify types and properties of the list
        for e in static_rules:
            # Verify type
            if not isinstance(e, MACPCIName):
                raise TypeError("Expected List of MACPCIName objects")

            # Verify kname is None
            if e.kname is not None:
                raise StaticRuleError("Expected static rule kname to be None")

            # Verify tname points to 'eth<foo>'
            if not e.tname.startswith("eth"):
                raise StaticRuleError("Static rule '%s' expected to name to "
                                      "'eth<num>'" % (e, ))

        # Verify no two static rules refer to the same eth name
        _ = frozenset( map(lambda x: x.tname, static_rules) )
        if len(_) != len(static_rules):
            raise StaticRuleError("Some static rules alias the same "
                                  "eth name")

        # Verify no two static rules refer to the same mac address
        _ = frozenset( map(lambda x: x.mac, static_rules) )
        if len(_) != len(static_rules):
            raise StaticRuleError("Some static rules alias the same MAC "
                                  "address")

    if len(cur_state):

        # Verify types and properties of the list
        for e in cur_state:
            if not isinstance(e, MACPCIName):
                raise TypeError("Expected List of MACPCIName objects")

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
        _ = frozenset( map(lambda x: x.kname, cur_state) )
        if len(_) != len(cur_state):
            raise CurrentStateError("Some entries of current state alias the "
                                    "same eth name")

        # Verify no two entries of current state refer to the same mac address
        _ = frozenset( map(lambda x: x.mac, cur_state) )
        if len(_) != len(cur_state):
            raise CurrentStateError("Some entries of current state alias the "
                                    "same MAC address")

    if len(last_state):

        # Verify types in the list
        for e in last_state:
            if not isinstance(e, MACPCIName):
                raise TypeError("Expected List of MACPCIName objects")

            # Verify kname is None
            if e.kname is not None:
                raise LastStateError("Expected last state kname to be None")

            # Verify kname is valid
            if VALID_ETH_NAME.match(e.tname) is None:
                raise LastStateError("Last state '%s' target name is invalid"
                                     % (e, ))


        # Verify no two entries of last state refer to the same eth name
        _ = frozenset( map(lambda x: x.tname, last_state) )
        if len(_) != len(last_state):
            raise LastStateError("Some entries of last state alias the "
                                 "same eth name")

        # Verify no two entries of last state refer to the same mac address
        _ = frozenset( map(lambda x: x.mac, last_state) )
        if len(_) != len(last_state):
            raise LastStateError("Some entries of last state alias the "
                                 "same MAC address")

    if len(old_state):

        # Verify types in the list
        for e in old_state:
            if not isinstance(e, MACPCIName):
                raise TypeError("Expected List of MACPCIName objects")

            # Verify tname is None
            if e.tname is not None:
                raise OldStateError("Expected last state tname to be None")

            # Verify kname points to 'eth<foo>'
            if not e.kname.startswith("eth"):
                raise OldStateError("Old state '%s' expected kname to "
                                      "'eth<num>'" % (e, ))


    return rename_logic(static_rules, cur_state, last_state, old_state)
