import unittest
import xcp.environ

class TestEnviron(unittest.TestCase):
    def test_read_inventory(self):
        inventory = xcp.environ.readInventory(root="tests/data/inventory")
        self.assertEqual(inventory["COMPANY_PRODUCT_BRAND"], 'XCP-ng')
        self.assertEqual(inventory["COMPANY_NAME"], 'Open Source')
