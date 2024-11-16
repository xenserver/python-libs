import pytest

from xcp.pci import pci_sbdfi_to_nic

nics = [
    # One PCI NIC may have multiple MACs, see the comment in xcp/pci.py:
    type("Nic", (object,), {"pci": "0000:01:00.0", "mac": "00:11:22:33:44:55"}),
    type("Nic", (object,), {"pci": "0000:01:00.0", "mac": "00:11:22:33:44:56"}),
    type("Nic", (object,), {"pci": "0000:02:00.0", "mac": "00:11:22:33:44:57"}),
]


def check_exc_info(exc_info, exc_type, sbdfi, nic_list):
    """Verify the raised exception to match the expected exception type and string"""
    if exc_info.type is not exc_type:  # Information for debugging fails:
        print("Unexpected exception raised at:\n", exc_info.traceback[1])

    assert exc_info.type is exc_type

    if len(sbdfi) >= 12 and len(sbdfi) <= 15:
        fmt = "Insufficient NICs with PCI SBDF {} (Found {}, wanted at least {})"
        index = 0 if len(sbdfi) <= 12 else sbdfi[13]
        found = 2 if len(sbdfi) >= 13 and sbdfi[:12] in [nic.pci for nic in nic_list] else 0
        assert exc_info.value.args[0] == fmt.format(sbdfi[:12], found, index)
    else:
        assert exc_info.value.args[0] == "'NoneType' object has no attribute 'groupdict'"


def check_raises(exc_type, func, sbdfi, nic_list):
    """Call pytest.raises() and check of the exact exception type and string"""
    with pytest.raises(exc_type) as exc_info:
        func(sbdfi, nic_list)

    check_exc_info(exc_info, exc_type, sbdfi, nic_list)


def test_sbdf_index():
    """Test all possible uses and xcp.pci.pci_sbdfi_to_nic() and raised Exceptions"""
    assert pci_sbdfi_to_nic("0000:01:00.0", nics) == nics[0]
    assert pci_sbdfi_to_nic("0000:01:00.0[0]", nics) == nics[0]
    assert pci_sbdfi_to_nic("0000:01:00.0[1]", nics) == nics[1]
    assert pci_sbdfi_to_nic("0000:02:00.0", nics) == nics[2]
    check_raises(Exception, pci_sbdfi_to_nic, "0000:03:00.0", nics)  # no matching SBDF
    check_raises(Exception, pci_sbdfi_to_nic, "0000:01:00.1[2]", nics)  # Not enough MACs
    check_raises(AttributeError, pci_sbdfi_to_nic, "0000:01:00.1[-1]", nics)  # Negative index
    check_raises(Exception, pci_sbdfi_to_nic, "0000:01:00.0", [])
    check_raises(AttributeError, pci_sbdfi_to_nic, "", nics)
    check_raises(AttributeError, pci_sbdfi_to_nic, "", [])
