import pytest

from xcp.pci import pci_sbdfi_to_nic

nics = [
    # One PCI NIC may have multiple MACs, see the comment in xcp/pci.py:
    type("Nic", (object,), {"pci": "0000:01:00.0", "mac": "00:11:22:33:44:55"}),
    type("Nic", (object,), {"pci": "0000:01:00.0", "mac": "00:11:22:33:44:56"}),
    type("Nic", (object,), {"pci": "0000:02:00.0", "mac": "00:11:22:33:44:57"}),
]


def test_sbdf_index():
    assert pci_sbdfi_to_nic("0000:01:00.0", nics) == nics[0]
    assert pci_sbdfi_to_nic("0000:01:00.0[0]", nics) == nics[0]
    assert pci_sbdfi_to_nic("0000:01:00.0[1]", nics) == nics[1]
    assert pci_sbdfi_to_nic("0000:02:00.0", nics) == nics[2]
    with pytest.raises(Exception) as e:
        pci_sbdfi_to_nic("0000:01:00.0[3]", nics)
        exp = "Insufficient NICs with PCI SBDF 0000:01:00.0 (Found 2, wanted at least 3)"
        assert str(e) == exp
    pytest.raises(Exception, pci_sbdfi_to_nic, "0000:03:00.0", nics)  # no matching SBDF
    pytest.raises(Exception, pci_sbdfi_to_nic, "0000:01:00.1[2]", nics)  # Not enough MACs
    pytest.raises(Exception, pci_sbdfi_to_nic, "0000:01:00.1[-1]", nics)  # Negative index
    pytest.raises(Exception, pci_sbdfi_to_nic, "0000:01:00.0", [])
    pytest.raises(Exception, pci_sbdfi_to_nic, "", nics)
    pytest.raises(Exception, pci_sbdfi_to_nic, "", [])
