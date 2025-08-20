"""tests/test_dmv.py: Unit test for xcp/dmv.py"""
import unittest
from unittest import mock
import types
import json
import errno
from xcp import dmv


class TestDMV(unittest.TestCase):
    @mock.patch("os.listdir")
    def test_get_all_kabi_dirs(self, m_listdir):
        m_listdir.return_value = ["4.19.0", "5.10.0"]
        dirs = dmv.get_all_kabi_dirs()
        self.assertIn(("4.19.0", "/lib/modules/4.19.0/updates", "/lib/modules/4.19.0/dmv"), dirs)
        self.assertIn(("5.10.0", "/lib/modules/5.10.0/updates", "/lib/modules/5.10.0/dmv"), dirs)

    def test_note_offset(self):
        self.assertEqual(dmv.note_offset(1), 3)
        self.assertEqual(dmv.note_offset(4), 0)
        self.assertEqual(dmv.note_offset(5), 3)

    def test_id_matches(self):
        self.assertTrue(dmv.id_matches("*", "1234"))
        self.assertTrue(dmv.id_matches("1234", "*"))
        self.assertTrue(dmv.id_matches("1234", "1234"))
        self.assertFalse(dmv.id_matches("1234", "5678"))

    def test_pci_matches_true(self):
        present = {"vendor": "14e4", "device": "163c", "subvendor": "*", "subdevice": "*"}
        driver_pci_ids = {
            "abc.ko": [
                {"vendor_id": "14e4", "device_id": "163c", "subvendor_id": "*", "subdevice_id": "*"}
            ]
        }
        self.assertTrue(dmv.pci_matches(present, driver_pci_ids))

    def test_pci_matches_false(self):
        present = {"vendor": "abcd", "device": "9999", "subvendor": "*", "subdevice": "*"}
        driver_pci_ids = {
            "abc.ko": [
                {"vendor_id": "14e4", "device_id": "163c", "subvendor_id": "*", "subdevice_id": "*"}
            ]
        }
        self.assertFalse(dmv.pci_matches(present, driver_pci_ids))

    @mock.patch("re.compile")
    def test_hardware_present_true(self, m_compile):
        m = mock.Mock()
        m.finditer.return_value = [
            mock.Mock(groupdict=lambda: {"vendor": "14e4", "device": "163c", "subvendor": "*", "subdevice": "*"})
        ]
        m_compile.return_value = m
        pci_ids = {
            "abc.ko": [
                {"vendor_id": "14e4", "device_id": "163c", "subvendor_id": "*", "subdevice_id": "*"}
            ]
        }
        self.assertTrue(dmv.hardware_present("dummy", pci_ids))

    @mock.patch("re.compile")
    def test_hardware_present_false_01(self, m_compile):
        self.assertFalse(dmv.hardware_present("dummy", None))

    @mock.patch("re.compile")
    def test_hardware_present_false_02(self, m_compile):
        m = mock.Mock()
        m.finditer.return_value = [
            mock.Mock(groupdict=lambda: {"vendor": "abcd", "device": "9999", "subvendor": "*", "subdevice": "*"})
        ]
        m_compile.return_value = m
        pci_ids = {
            "abc.ko": [
                {"vendor_id": "14e4", "device_id": "163c", "subvendor_id": "*", "subdevice_id": "*"}
            ]
        }
        self.assertFalse(dmv.hardware_present("dummy", pci_ids))

    @mock.patch("os.path.isfile")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("struct.calcsize")
    @mock.patch("struct.unpack")
    def test_get_active_variant(self, m_unpack, m_calcsize, m_open, m_isfile):
        m_isfile.return_value = True
        m_calcsize.return_value = 12
        m_unpack.return_value = (9, 3, 1)
        fake_file = mock.Mock()
        fake_file.read.side_effect = [
            b"x"*12,  # header
            b"",      # offset
            b"XenServer", b"", b"v1\x00", b"",  # vendor, offset, content, offset
        ]
        m_open.return_value.__enter__.return_value = fake_file
        result = dmv.get_active_variant(["foo.ko"])
        self.assertEqual(result, "v1")

        m_isfile.return_value = False
        result = dmv.get_active_variant(["foo.ko"])
        self.assertEqual(result, None)

    @mock.patch("os.path.isfile")
    def test_get_loaded_modules(self, m_isfile):
        m_isfile.side_effect = lambda path: "foo" in path
        result = dmv.get_loaded_modules(["foo.ko", "bar.ko"])
        self.assertEqual(result, ["foo.ko"])

    @mock.patch("os.path.islink")
    @mock.patch("os.path.realpath")
    @mock.patch("os.path.dirname")
    @mock.patch("builtins.open", new_callable=mock.mock_open, read_data='{"variant": "v1"}')
    @mock.patch("json.load")
    def test_variant_selected(self, m_json_load, m_open, m_dirname, m_realpath, m_islink):
        m_islink.return_value = True
        m_realpath.return_value = "/some/dir"
        m_dirname.return_value = "/some/dir"
        m_json_load.return_value = {"variant": "v1"}
        d = dmv.DriverMultiVersion("/updates", None)
        result = d.variant_selected(["foo.ko"])
        self.assertEqual(result, "v1")

        m_islink.return_value = False
        d = dmv.DriverMultiVersion("/updates", None)
        result = d.variant_selected(["foo.ko"])
        self.assertEqual(result, None)

    @mock.patch("xcp.dmv.open_with_codec_handling")
    @mock.patch("xcp.dmv.hardware_present")
    def test_parse_dmv_info01(self, m_hw_present, m_open_codec):
        m_hw_present.return_value = True
        info_json = {
            "category": "net",
            "name": "foo",
            "description": "desc",
            "variant": "v1",
            "version": "1.0",
            "priority": 1,
            "status": "ok",
            "pci_ids": {
                "foo.ko": [
                    {"vendor_id": "14e4", "device_id": "163c", "subvendor_id": "*", "subdevice_id": "*"}
                ]
            }
        }
        m_open_codec.return_value.__enter__.return_value = mock.Mock(
            spec=["read"], read=lambda: json.dumps(info_json)
        )
        with mock.patch("json.load", return_value=info_json):
            lspci_out = types.SimpleNamespace(stdout="dummy")
            d = dmv.DriverMultiVersion("", lspci_out)
            json_data, json_formatted = d.parse_dmv_info("dummy")
            self.assertEqual(json_data["name"], "foo")
            self.assertEqual(json_formatted["type"], "net")
            self.assertTrue(json_formatted["variants"]["v1"]["hardware_present"])

    @mock.patch("xcp.dmv.open_with_codec_handling")
    @mock.patch("xcp.dmv.hardware_present")
    @mock.patch("xcp.dmv.get_active_variant")
    def test_parse_dmv_info02(self, m_active_variant, m_hw_present, m_open_codec):
        m_active_variant.return_value = "foo"
        m_hw_present.return_value = True
        info_json = {
            "category": "net",
            "name": "foo",
            "description": "desc",
            "variant": "v1",
            "version": "1.0",
            "priority": 1,
            "status": "ok",
            "pci_ids": {
                "foo.ko": [
                    {"vendor_id": "14e4", "device_id": "163c", "subvendor_id": "*", "subdevice_id": "*"}
                ]
            }
        }
        m_open_codec.return_value.__enter__.return_value = mock.Mock(
            spec=["read"], read=lambda: json.dumps(info_json)
        )
        with mock.patch("json.load", return_value=info_json):
            lspci_out = types.SimpleNamespace(stdout="dummy")
            d = dmv.DriverMultiVersion("", lspci_out, runtime=True)
            json_data, json_formatted = d.parse_dmv_info("dummy")
            self.assertEqual(json_data["name"], "foo")
            self.assertEqual(json_formatted["type"], "net")
            self.assertTrue(json_formatted["variants"]["v1"]["hardware_present"])
            self.assertEqual(json_formatted["active"], "foo")

    def test_merge_jsondata01(self):
        oldone = {
            "type": "net",
            "friendly_name": "foo",
            "description": "desc",
            "info": "foo",
            "variants": {"v1": {"version": "1.0"}},
            "selected": "v1",
            "active": "v1",
            "loaded modules": ["foo.ko"]
        }
        newone = {
            "type": "net",
            "friendly_name": "foo",
            "description": "desc",
            "info": "foo",
            "variants": {"v2": {"version": "2.0"}},
            "selected": None,
            "active": None,
            "loaded modules": ["bar.ko"]
        }
        mgr = dmv.DriverMultiVersionManager(runtime=True)
        mgr.merge_jsondata(oldone, newone)
        merged = mgr.dmv_list["drivers"]["foo"]
        self.assertIn("v1", merged["variants"])
        self.assertIn("v2", merged["variants"])
        self.assertEqual(merged["selected"], "v1")
        self.assertEqual(merged["active"], "v1")
        self.assertEqual(merged["loaded modules"], ["foo.ko", "bar.ko"])

    def test_merge_jsondata02(self):
        oldobj = {
            "type": "storage",
            "friendly_name": "foo",
            "description": "desc",
            "info": "foo",
            "variants": {"v1": {"version": "1.0"}},
            "selected": None,
            "active": None,
            "loaded modules": ["foo.ko"]
        }
        newobj = {
            "type": "storage",
            "friendly_name": "foo",
            "description": "desc",
            "info": "foo",
            "variants": {"v2": {"version": "2.0"}},
            "selected": "v2",
            "active": "v2",
            "loaded modules": ["bar.ko"]
        }
        mgr = dmv.DriverMultiVersionManager(runtime=True)
        mgr.merge_jsondata(oldobj, newobj)
        merged = mgr.dmv_list["drivers"]["foo"]
        self.assertIn("v1", merged["variants"])
        self.assertIn("v2", merged["variants"])
        self.assertEqual(merged["selected"], "v2")
        self.assertEqual(merged["active"], "v2")
        self.assertEqual(merged["loaded modules"], ["foo.ko", "bar.ko"])

    def test_process_dmv_data(self):
        mgr = dmv.DriverMultiVersionManager()
        json_data = {"name": "foo"}
        json_formatted = {"type": "net"}
        mgr.process_dmv_data(json_data, json_formatted)
        self.assertEqual(mgr.dmv_list["drivers"]["foo"], json_formatted)

    @mock.patch("xcp.dmv.subprocess.run")
    @mock.patch("xcp.dmv.glob.glob")
    @mock.patch("xcp.dmv.os.makedirs")
    @mock.patch("xcp.dmv.os.symlink")
    @mock.patch("xcp.dmv.os.rename")
    @mock.patch("xcp.dmv.os.path.join", side_effect=lambda *args: "/".join(args))
    @mock.patch("xcp.dmv.get_all_kabi_dirs")
    def test_create_dmv_symlink(self, m_get_dirs, m_join, m_rename, m_symlink, m_makedirs, m_glob, m_run):
        m_get_dirs.return_value = [("5.10.0", "/lib/modules/5.10.0/updates", "/lib/modules/5.10.0/dmv")]
        m_glob.return_value = ["/lib/modules/5.10.0/dmv/foo/1.0/bar.ko"]
        m_symlink.side_effect = None
        m_rename.side_effect = None
        m_run.side_effect = None

        mgr = dmv.DriverMultiVersionManager()
        result = mgr.create_dmv_symlink("foo", "1.0")
        self.assertTrue(result)
        m_makedirs.assert_called_with("/lib/modules/5.10.0/updates", exist_ok=True)
        m_symlink.assert_called()
        m_rename.assert_called()

    def test_get_set_error(self):
        mgr = dmv.DriverMultiVersionManager()
        mgr.set_dmv_error(errno.ENOENT)
        err = mgr.get_dmv_error()
        self.assertEqual(err["exit_code"], errno.ENOENT)
        self.assertIn("No such file", err["message"])
