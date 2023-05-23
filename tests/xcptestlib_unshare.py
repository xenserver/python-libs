import ctypes
import os

CLONE_NEWUSER = 0x10000000
CLONE_NEWNET = 0x40000000


def libc_unshare_syscall(flags):
    """Wrapper for the unshare(2) libc function/system call to disassociate parts of the ucontext"""
    libc = ctypes.CDLL(None, use_errno=True)
    libc.unshare.argtypes = [ctypes.c_int]
    rc = libc.unshare(flags)
    if rc != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), flags)


def disassociate_namespaces(namespaces):
    """unshare/disassociate parts of the process execution context and switch to new namespaces"""
    uidmap = b"0 %d 1" % os.getuid()  # uidmap for the current uid in the new namespace
    libc_unshare_syscall(namespaces)
    if namespaces & CLONE_NEWUSER:  # Become root in the new user namespace if we created one:
        with open("/proc/self/uid_map", "wb") as file_:
            file_.write(uidmap)  #  Switch to uid=0 in the namespace to have root privileges
