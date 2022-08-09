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
        for line in proc.stdout:
            # FIXME: check is entirely ad-hoc, should we have a diff at all ?
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

    def test_grub(self):
        with NamedTemporaryFile("w", delete=False) as temp:
            self.bl.writeGrub(temp)
        bl2 = Bootloader.readGrub(temp.name)
        os.unlink(temp.name)

    def test_extlinux(self):
        with NamedTemporaryFile("w", delete=False) as temp:
            self.bl.writeExtLinux(temp)
        bl2 = Bootloader.readExtLinux(temp.name)
        os.unlink(temp.name)
