import unittest
import os
import shutil
import subprocess
from tempfile import NamedTemporaryFile, mkdtemp

from xcp.bootloader import Bootloader
from xcp.compat import open_with_codec_handling


class TestBootloader(unittest.TestCase):
    def test_grub2(self):
        bl = Bootloader.readGrub2("tests/data/grub.cfg")
        with NamedTemporaryFile("w") as temp:
            bl.writeGrub2(temp.name)
            # get a diff
            proc = subprocess.Popen(["diff", "tests/data/grub.cfg", temp.name],
                                    stdout = subprocess.PIPE,
                                    universal_newlines=True)
        assert proc.stdout
        for line in proc.stdout:
            # pylint: disable-next=deprecated-method
            self.assertRegexpMatches(line, r"^(5a6,13$|>)")

        proc.stdout.close()
        proc.wait()

    def test_no_multiboot(self):
        # A module2 line without a multiboot2 line is an error
        with self.assertRaises(RuntimeError):
            Bootloader.readGrub2("tests/data/grub-no-multiboot.cfg")

class TestLinuxBootloader(unittest.TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp(prefix="testbl")
        bootdir = os.path.join(self.tmpdir, "boot")
        grubdir = os.path.join(bootdir, "grub")
        os.makedirs(grubdir)
        shutil.copyfile("tests/data/grub-linux.cfg", os.path.join(grubdir, "grub.cfg"))
        with open_with_codec_handling(os.path.join(bootdir, "vmlinuz-1"), "w"):
            pass
        with open_with_codec_handling(os.path.join(bootdir, "vmlinuz-2"), "w"):
            pass
        with open_with_codec_handling(os.path.join(bootdir, "initrd.img-1"), "w"):
            pass
        with open_with_codec_handling(os.path.join(bootdir, "initrd.img-2"), "w"):
            pass
    def tearDown(self):
        shutil.rmtree(self.tmpdir)
    def test_grub2_newdefault(self):
        Bootloader.newDefault("/boot/vmlinuz-2", "/boot/initrd.img-2", root=self.tmpdir)
        bl = Bootloader.loadExisting(root=self.tmpdir)
        assert bl.boilerplate == [
            [
                "# set default=0 is disabled to cover boilerplate generation code",
                "if [ -s $prefix/grubenv ]; then",
                "\tload_env",
                "fi",
                "",
                'if [ -n "$override_entry" ]; then',
                "\tset default=$override_entry",
                "fi",
                "",
            ],
            [],
        ]
        assert str(bl.default).startswith("safe")
        assert bl.location == "mbr"
        assert bl.menu["safe"].hypervisor is None
        assert bl.menu["safe"].hypervisor_args is None
        assert bl.menu["safe"].title == "Linux - Safe Mode"
        assert bl.menu["safe"].kernel == "/boot/vmlinuz-2"
        assert bl.menu["safe"].kernel_args == "ro"
        assert bl.menu["safe"].initrd == "/boot/initrd.img-2"

class TestBootloaderAdHoc(unittest.TestCase):
    def setUp(self):
        self.bl = Bootloader.readGrub2("tests/data/grub.cfg")
        check_config(self.bl)

    def test_grub2(self):
        with NamedTemporaryFile("w", delete=False) as temp:
            self.bl.writeGrub2(temp)
        bl2 = Bootloader.readGrub2(temp.name)
        # Check config from tests/data/grub.cfg:
        os.unlink(temp.name)
        assert bl2.serial == {"port": 0, "baud": 115200}
        check_config(bl2)


def check_config(bl):
    # Check config from tests/data/grub.cfg:
    assert bl.timeout == 50  # xcp.bootloader multiples and divides the timeout by 10
    assert bl.default == "xe"
    assert bl.location == "mbr"
    assert sorted(bl.menu.keys()) == sorted(
        ["xe", "xe-serial", "safe", "fallback", "fallback-serial"]
    )
    assert bl.menu["xe"].title == "XCP-ng"
    assert bl.menu["xe"].hypervisor == "/boot/xen.gz"
    assert bl.menu["xe"].hypervisor_args == " ".join(
        (
            "dom0_mem=7584M,max:7584M",
            "watchdog",
            "ucode=scan",
            "dom0_max_vcpus=1-16",
            "crashkernel=256M,below=4G",
            "console=vga",
            "vga=mode-0x0311",
        )
    )
    assert bl.menu["xe"].kernel == "/boot/vmlinuz-4.19-xen"
    assert bl.menu["xe"].kernel_args == " ".join(
        (
            "root=LABEL=root-vgdorj",
            "ro",
            "nolvm",
            "hpet=disable",
            "console=hvc0",
            "console=tty0",
            "quiet",
            "vga=785",
            "splash",
            "plymouth.ignore-serial-consoles",
        )
    )
    assert bl.menu["xe"].initrd == "/boot/initrd-4.19-xen.img"
