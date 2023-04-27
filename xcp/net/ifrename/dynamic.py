#!/usr/bin/env python

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
Object for manipulating dynamic rules.

The dynamic rules file on disk is a JSON file with optional line comments
beginning with a # character.
"""

from __future__ import unicode_literals

__version__ = "1.0.0"
__author__  = "Andrew Cooper"

try:
    import json
except ImportError:
    try:
        import simplejson as json  # type: ignore  # mypy sees the import above
    # The installer has no json.  In the meantime, there is a workaround
    except ImportError:
        pass


from xcp.logger import LOG
from xcp.net.ifrename.macpci import MACPCI
from xcp.pci import pci_sbdfi_to_nic
from os.path import exists as pathexists

SAVE_HEADER = (
    "# Automatically adjusted file.  Do not edit unless you are "
    "certain you know how to\n"
    )


class DynamicRules(object):
    """
    Object for parsing the dynamic rules configuration.

    There are two distinct usecases; the installer needs to write the
    dynamic rules from scratch, whereas interface-rename.py in dom0 needs
    to read and write them.
    """

    def __init__(self, path=None, fd=None):

        self.path = path
        self.fd = fd

        self.lastboot = []
        self.old = []

        self.formulae = {}
        self.rules = []

    def load_and_parse(self):
        """
        Parse the dynamic rules file.
        Returns boolean indicating success or failure.
        """

        fd = None

        try:
            try:
                # If we were given a path, try opening and reading it
                if self.path:
                    if not pathexists(self.path):
                        LOG.error("Dynamic rule file '%s' does not exist"
                                  % (self.path,))
                        return False
                    fd = open(self.path, "r")
                    raw_lines = fd.readlines()

                # else if we were given a file descriptor, just read it
                elif self.fd:
                    raw_lines = self.fd.readlines()

                # else there is nothing we can do
                else:
                    LOG.error("No source of data to parse")
                    return False

            except IOError as e:
                LOG.error("IOError while reading file: %s" % (e,))
                return False
        finally:
            # Ensure we alway close the file descriptor we opened
            if fd:
                fd.close()

        # Strip out line comments
        data = "\n".join([ l.strip() for l in raw_lines
                           if len(l.strip()) and l.strip()[0] != '#' ]
                         )

        # If the data is empty, dont pass it to json
        if not len( data.strip() ):
            return True

        try:
            info = json.loads(data)
        except ValueError:
            LOG.warning("Dynamic rules appear to be corrupt")
            return False
        # The installer has no json.
        except NameError:
            LOG.warning("Module json not available.  Cant parse dynamic rules.")
            return False

        if "lastboot" in info:
            for entry in info["lastboot"]:
                try:
                    if len(entry) != 3:
                        raise ValueError("Expected 3 entries")
                    macpci = MACPCI(entry[0], entry[1], tname=entry[2])
                except (TypeError, ValueError) as e:
                    LOG.warning("Invalid lastboot data entry: %s"
                                % (e,))
                    continue
                self.lastboot.append(macpci)

        if "old" in info:
            for entry in info["old"]:
                try:
                    if len(entry) != 3:
                        raise ValueError("Expected 3 entries")
                    macpci = MACPCI(entry[0], entry[1], tname=entry[2])
                except (TypeError, ValueError) as e:
                    LOG.warning("Invalid old data entry: %s" % (e,))
                    continue
                self.old.append(macpci)

        return True

    def generate(self, state):
        """
        Make rules from the formulae based on global state.
        """

        # CA-75599 - check that state has no shared ppns.
        #  See net.biodevname.has_ppn_quirks() for full reason
        ppns = [ x.ppn for x in state if x.ppn is not None ]
        ppn_quirks = ( len(ppns) != len(set(ppns)) )

        if ppn_quirks:
            LOG.warning("Discovered physical policy naming quirks in provided "
                        "state.  Disabling 'method=ppn' generation")

        for target, (method, value) in self.formulae.items():

            if method == "mac":

                for nic in state:
                    if nic.mac == value:
                        try:
                            rule = MACPCI(nic.mac, nic.pci, tname=target)
                        except Exception as e:
                            LOG.warning("Error creating rule: %s" % (e,))
                            continue
                        self.rules.append(rule)
                        break
                else:
                    LOG.warning("No NIC found with a MAC address of '%s' for "
                                "the %s dynamic rule" % (value, target))
                continue

            elif method == "ppn":

                if ppn_quirks:
                    LOG.info("Not considering formula for '%s' due to ppn "
                             "quirks" % (target,))
                    continue

                for nic in state:
                    if nic.ppn == value:
                        try:
                            rule = MACPCI(nic.mac, nic.pci, tname=target)
                        except Exception as e:
                            LOG.warning("Error creating rule: %s" % (e,))
                            continue
                        self.rules.append(rule)
                        break
                else:
                    LOG.warning("No NIC found with a ppn of '%s' for the "
                                "%s dynamic rule" % (value, target))
                continue

            elif method == "pci":
                try:
                    nic = pci_sbdfi_to_nic(value, state)
                    rule = MACPCI(nic.mac, nic.pci, tname=target)
                except Exception as e:
                    LOG.warning("Error creating rule: %s" % (e,))
                    continue
                self.rules.append(rule)

                continue

            elif method == "label":

                for nic in state:
                    if nic.label == value:
                        try:
                            rule = MACPCI(nic.mac, nic.pci, tname=target)
                        except Exception as e:
                            LOG.warning("Error creating rule: %s" % (e,))
                            continue
                        self.rules.append(rule)
                        break
                else:
                    LOG.warning("No NIC found with an SMBios Label of '%s' for "
                                "the %s dynamic rule" % (value, target))
                continue

            else:
                LOG.critical("Unknown dynamic rule method %s" % method)


    def write(self, header = True):
        """
        Write the dynamic rules to a string
        """

        res = ""

        if header:
            res += SAVE_HEADER

        def validate(entry):
            try:
                # iBFT NICs are ignored so don't have a tname
                if entry[2] is None:
                    return False
                MACPCI(entry[0], entry[1], tname=entry[2])
                return True
            except Exception as e:
                LOG.warning("Failed to validate '%s' because '%s'"
                            % (entry, e))
                return False

        lastboot = [x for x in self.lastboot if validate(x)]
        old = [x for x in self.old if validate(x)]

        try:
            res += json.dumps({"lastboot": lastboot, "old": old},
                              indent=4, sort_keys=True)
            # Installer has no json.  This will do in the meantime
        except NameError:
            res += ('{"lastboot":%s,"old":%s}'
                    % ( ("%s" % (lastboot,)).replace("'", '"'),
                        ("%s" % (old,)).replace("'", '"'))
                    )

        return res

    def save(self, header = True):
        """
        Save the dynamic rules to a file/path.
        Returns boolean indicating success or failure.
        """

        fd = None

        try:
            try:
                # If we were given a path, try opening and writing to it
                if self.path:
                    fd = open(self.path, "w")
                    fd.write(self.write(header))

                # else if we were given a file descriptor, just write to it
                elif self.fd:
                    self.fd.write(self.write(header))

                # else there is nothing we can do
                else:
                    LOG.error("No source of data to parse")
                    return False

            except IOError as e:
                LOG.error("IOError while reading file: %s" % (e,))
                return False
        finally:
            # Ensure we alway close the file descriptor we opened
            if fd:
                fd.close()

        return True
