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
Object for manipulating dynamic rules.

The dynamic rules file on disk is a JSON file with optional line comments
beginning with a # character.
"""

__version__ = "1.0.0"
__author__  = "Andrew Cooper"

try:
    import json
except ImportError:
    try:
        import simplejson as json
    # The installer has no json.  In the meantime, there is a workaround
    except ImportError:
        pass


from xcp.logger import LOG
from xcp.net.ifrename.macpci import MACPCI
from os.path import exists as pathexists

SAVE_HEADER = (
    "# Automatically adjusted file.  Do not edit unless you are"
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
                        LOG.error("Static rule file '%s' does not exist"
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

            except IOError, e:
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
                except (TypeError, ValueError), e:
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
                except (TypeError, ValueError), e:
                    LOG.warning("Invalid old data entry: %s" % (e,))
                    continue
                self.old.append(macpci)

        return True

    def generate(self, state):
        """
        Make rules from the formulae based on global state.
        """

        for target, (method, value) in self.formulae.iteritems():

            if method == "mac":

                for nic in state:
                    if nic.mac == value:
                        try:
                            rule = MACPCI(nic.mac, nic.pci, tname=target)
                        except Exception, e:
                            LOG.warning("Error creating rule: %s" % (e,))
                            continue
                        self.rules.append(rule)
                        break
                else:
                    LOG.warning("No NIC found with a MAC address of '%s' for "
                                "the %s dynamic rule" % (value, target))
                continue

            elif method == "ppn":

                for nic in state:
                    if nic.ppn == value:
                        try:
                            rule = MACPCI(nic.mac, nic.pci, tname=target)
                        except Exception, e:
                            LOG.warning("Error creating rule: %s" % (e,))
                            continue
                        self.rules.append(rule)
                        break
                else:
                    LOG.warning("No NIC found with a ppn of '%s' for the "
                                "%s dynamic rule" % (value, target))
                continue

            elif method == "pci":

                for nic in state:
                    if nic.pci == value:
                        try:
                            rule = MACPCI(nic.mac, nic.pci, tname=target)
                        except Exception, e:
                            LOG.warning("Error creating rule: %s" % (e,))
                            continue
                        self.rules.append(rule)
                        break
                else:
                    LOG.warning("No NIC found with a PCI ID of '%s' for the "
                                "%s dynamic rule" % (value, target))
                continue

            elif method == "label":

                for nic in state:
                    if nic.label == value:
                        try:
                            rule = MACPCI(nic.mac, nic.pci, tname=target)
                        except Exception, e:
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
                MACPCI(entry[0], entry[1], tname=entry[2])
                return True
            except Exception, e:
                LOG.warning("Failed to validate '%s' because '%s'"
                            % (entry, e))
                return False

        lastboot = filter(validate, self.lastboot)
        old = filter(validate, self.old)

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
                    if not pathexists(self.path):
                        LOG.error("Dynamic rule file '%s' does not exist"
                                  % (self.path,))
                        return False
                    fd = open(self.path, "w")
                    fd.write(self.write(header))

                # else if we were given a file descriptor, just write to it
                elif self.fd:
                    self.fd.write(self.write(header))

                # else there is nothing we can do
                else:
                    LOG.error("No source of data to parse")
                    return False

            except IOError, e:
                LOG.error("IOError while reading file: %s" % (e,))
                return False
        finally:
            # Ensure we alway close the file descriptor we opened
            if fd:
                fd.close()

        return True
