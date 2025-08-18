import unittest
import os
import shutil
import subprocess
from tempfile import NamedTemporaryFile, mkdtemp

from xcp.bootloader import Bootloader, Grub2Format, MenuEntry
from xcp.compat import open_with_codec_handling


class TestBootloader(unittest.TestCase):
    def _test_cfg(self, cfg):
        bl = Bootloader.readGrub2(cfg)
        with NamedTemporaryFile("w") as temp:
            bl.writeGrub2(temp.name)
            # get a diff
            proc = subprocess.Popen(["diff", cfg, temp.name],
                                    stdout = subprocess.PIPE,
                                    universal_newlines=True)

            assert proc.stdout is not None  # for pyright, to ensure it is valid
            # check the diff output, working around trailing whitespace issues
            self.assertEqual(proc.stdout.read(), '''5a6,13
> if [ -s $prefix/grubenv ]; then
> 	load_env
> fi
> ''' + '''
> if [ -n "$override_entry" ]; then
> 	set default=$override_entry
> fi
> ''' + '''
''')
            proc.stdout.close()
            proc.wait()
            self.assertEqual(proc.returncode, 1)

    def test_grub2(self):
        '''Test read/write roundtrip of GRUB2 multiboot config'''
        self._test_cfg("tests/data/grub.cfg")

    def test_grub2_xen_boot(self):
        '''Test read/write roundtrip of GRUB2 xen_boot config'''
        self._test_cfg("tests/data/grub-xen-boot.cfg")

    def test_no_multiboot(self):
        # A module2 line without a multiboot2 line is an error
        with self.assertRaises(RuntimeError):
            Bootloader.readGrub2("tests/data/grub-no-multiboot.cfg")

    def test_no_hypervisor(self):
        # A xen_module line without a xen_hypervisor line is an error
        with self.assertRaises(RuntimeError):
            Bootloader.readGrub2("tests/data/grub-no-hypervisor.cfg")


class TestMenuEntry(unittest.TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp(prefix="testbl")
        self.fn = os.path.join(self.tmpdir, 'grub.cfg')
        self.bl = Bootloader('grub2', self.fn)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_new_multiboot(self):
        # No format specified, default to multiboot2
        e = MenuEntry(hypervisor='xen.efi', hypervisor_args='xarg1 xarg2',
                      kernel='vmlinuz', kernel_args='karg1 karg2',
                      initrd='initrd.img', title='xe')
        self.bl.append('xe', e)

        e = MenuEntry(hypervisor='xen.efi', hypervisor_args='xarg1 xarg2',
                      kernel='vmlinuz', kernel_args='karg1 karg2',
                      initrd='initrd.img', title='xe-serial')
        e.entry_format = Grub2Format.MULTIBOOT2
        self.bl.append('xe-serial', e)

        self.bl.commit()

        with open_with_codec_handling(self.fn, 'r') as f:
            content = f.read()

        self.assertEqual(content, '''menuentry 'xe' {
	multiboot2 xen.efi xarg1 xarg2
	module2 vmlinuz karg1 karg2
	module2 initrd.img
}
menuentry 'xe-serial' {
	multiboot2 xen.efi xarg1 xarg2
	module2 vmlinuz karg1 karg2
	module2 initrd.img
}
''')

    def test_new_xen_boot(self):
        e = MenuEntry(hypervisor='xen.efi', hypervisor_args='xarg1 xarg2',
                      kernel='vmlinuz', kernel_args='karg1 karg2',
                      initrd='initrd.img', title='xe')
        e.entry_format = Grub2Format.XEN_BOOT
        self.bl.append('xe', e)
        self.bl.commit()

        with open_with_codec_handling(self.fn, 'r') as f:
            content = f.read()

        self.assertEqual(content, '''menuentry 'xe' {
	xen_hypervisor xen.efi xarg1 xarg2
	xen_module vmlinuz karg1 karg2
	xen_module initrd.img
}
''')

    def test_new_linux(self):
        e = MenuEntry(hypervisor='', hypervisor_args='',
                      kernel='vmlinuz', kernel_args='karg1 karg2',
                      initrd='initrd.img', title='linux')
        self.bl.append('linux', e)
        self.bl.commit()

        e = MenuEntry(hypervisor='', hypervisor_args='',
                      kernel='vmlinuz2', kernel_args='karg3 karg4',
                      initrd='initrd2.img', title='linux2')
        e.entry_format = Grub2Format.LINUX
        self.bl.append('linux2', e)
        self.bl.commit()

        with open_with_codec_handling(self.fn, 'r') as f:
            content = f.read()

        self.assertEqual(content, '''menuentry 'linux' {
	linux vmlinuz karg1 karg2
	initrd initrd.img
}
menuentry 'linux2' {
	linux vmlinuz2 karg3 karg4
	initrd initrd2.img
}
''')


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

    def test_no_kernel(self):
        # An initrd line without a kernel line is an error
        with self.assertRaises(RuntimeError):
            Bootloader.readGrub2("tests/data/grub-linux-no-kernel.cfg")


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
