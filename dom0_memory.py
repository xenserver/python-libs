#
# Copyright (C) 2012 Citrix Systems (UK) Ltd.
#

def default_dom0_memory(host_mem_kib):
    """Return the default for the amount of dom0 memory for the
    specified amount of host memory."""

    #
    # The host memory reported by Xen is a bit less than the physical
    # RAM installed in the machine since it doesn't include the memory
    # used by Xen etc.
    #
    # Add a bit extra to account for this.
    #
    gb = (host_mem_kib + 256 * 1024) / 1024 / 1024

    if gb < 24:
        return 752 * 1024
    elif gb < 48:
        return 2 * 1024 * 1024
    elif gb < 64:
        return 3 * 1024 * 1024
    else:
        return 4 * 1024 * 1024
