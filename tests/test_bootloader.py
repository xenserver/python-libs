import unittest
import os
import shutil
import subprocess
from tempfile import NamedTemporaryFile, mkdtemp

from xcp.bootloader import Bootloader

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

class TestLinuxBootloader(unittest.TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp(prefix="testbl")
        bootdir = os.path.join(self.tmpdir, "boot")
        grubdir = os.path.join(bootdir, "grub")
        os.makedirs(grubdir)
        shutil.copyfile("tests/data/grub-linux.cfg", os.path.join(grubdir, "grub.cfg"))
        with open(os.path.join(bootdir, "vmlinuz-1"), "w"):
            pass
        with open(os.path.join(bootdir, "vmlinuz-2"), "w"):
            pass
        with open(os.path.join(bootdir, "initrd.img-1"), "w"):
            pass
        with open(os.path.join(bootdir, "initrd.img-2"), "w"):
            pass
    def tearDown(self):
        shutil.rmtree(self.tmpdir)
    def test_grub2_newdefault(self):
        Bootloader.newDefault("/boot/vmlinuz-2", "/boot/initrd.img-2", root=self.tmpdir)

class TestBootloaderAdHoc(unittest.TestCase):
    def setUp(self):
        self.bl = Bootloader.readGrub2("tests/data/grub.cfg")
        check_config(self.bl)

    def test_grub(self):
        with NamedTemporaryFile("w", delete=False) as temp:
            self.bl.writeGrub(temp)
        bl2 = Bootloader.readGrub(temp.name)
        # Check config from tests/data/grub.cfg:
        os.unlink(temp.name)
        assert bl2.serial == {"port": 0, "baud": 115200}
        check_config(bl2)

    def test_extlinux(self):
        with NamedTemporaryFile("w", delete=False) as temp:
            self.bl.writeExtLinux(temp)
        bl2 = Bootloader.readExtLinux(temp.name)
        os.unlink(temp.name)
        # readExtLinux tries to read flow-control (there is none in tests/data/grub.cfg):
        assert bl2.serial == {"port": 0, "baud": 115200, "flow": None}
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
