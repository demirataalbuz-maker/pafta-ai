"""Real narrow Windows Deny ACEs on newly created test-owned objects only.

Retain WRITE_DAC handles before denying reads; restore the original DACL in
finally, then delete just the owned leaf. Never touches existing system keys.
API contracts: Microsoft GetSecurityInfo, SetSecurityInfo, SetEntriesInAclW.
"""
from contextlib import contextmanager
import csv
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import subprocess
import uuid
import winreg

ADV=C.WinDLL('advapi32',use_last_error=True)
KERNEL=C.WinDLL('kernel32',use_last_error=True)
P=C.c_void_p
PP=C.POINTER(P)


class Trustee(C.Structure):
    _fields_=[('multiple',P),('operation',W.DWORD),('form',W.DWORD),('kind',W.DWORD),('name',P)]


class ExplicitAccess(C.Structure):
    _fields_=[('permissions',W.DWORD),('mode',W.DWORD),('inheritance',W.DWORD),('trustee',Trustee)]


ADV.GetSecurityInfo.argtypes=[W.HANDLE,W.DWORD,W.DWORD,PP,PP,PP,PP,PP]
ADV.GetSecurityInfo.restype=W.DWORD
ADV.SetSecurityInfo.argtypes=[W.HANDLE,W.DWORD,W.DWORD,P,P,P,P]
ADV.SetSecurityInfo.restype=W.DWORD
ADV.SetEntriesInAclW.argtypes=[W.DWORD,C.POINTER(ExplicitAccess),P,PP]
ADV.SetEntriesInAclW.restype=W.DWORD
ADV.ConvertStringSidToSidW.argtypes=[W.LPCWSTR,PP]
ADV.ConvertStringSidToSidW.restype=W.BOOL
KERNEL.LocalFree.argtypes=[P]
KERNEL.LocalFree.restype=P
KERNEL.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,P,W.DWORD,W.DWORD,W.HANDLE]
KERNEL.CreateFileW.restype=W.HANDLE
KERNEL.CloseHandle.argtypes=[W.HANDLE]
KERNEL.CloseHandle.restype=W.BOOL


def checked(code):
    if code:raise C.WinError(code)


def current_sid():
    result=subprocess.run(['whoami.exe','/user','/fo','csv','/nh'],capture_output=True,check=True)
    rows=list(csv.reader(result.stdout.decode('utf-8-sig',errors='replace').splitlines()))
    sid=rows[0][1]
    if not sid.startswith('S-1-'):raise RuntimeError('Current user SID missing')
    return sid


class OwnedDacl:
    def __init__(self,handle,kind):
        self.handle=handle;self.kind=kind
        self.original=P();self.descriptor=P()
        checked(ADV.GetSecurityInfo(handle,kind,4,None,None,C.byref(self.original),None,C.byref(self.descriptor)))

    def deny_read(self):
        sid=P();acl=P()
        if not ADV.ConvertStringSidToSidW(current_sid(),C.byref(sid)):
            raise C.WinError(C.get_last_error())
        try:
            # Bit 1 is FILE_READ_DATA or KEY_QUERY_VALUE. Not READ_CONTROL,
            # WRITE_DAC, DELETE or a broad FullControl/ReadKey denial.
            entry=ExplicitAccess(1,3,0,Trustee(None,0,0,1,sid))
            checked(ADV.SetEntriesInAclW(1,C.byref(entry),self.original,C.byref(acl)))
            checked(ADV.SetSecurityInfo(self.handle,self.kind,4,None,None,acl,None))
        finally:
            if acl:KERNEL.LocalFree(acl)
            KERNEL.LocalFree(sid)

    def restore(self):
        checked(ADV.SetSecurityInfo(self.handle,self.kind,4,None,None,self.original,None))

    def close(self):
        try:self.restore()
        finally:KERNEL.LocalFree(self.descriptor)


@contextmanager
def registry_fixture():
    path=r'Software\PaftaCmd_'+uuid.uuid4().hex
    key=winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,path,0,winreg.KEY_ALL_ACCESS)
    dacl=None
    try:
        winreg.SetValueEx(key,'PaftaValue',0,winreg.REG_SZ,'LAB_ONLY')
        dacl=OwnedDacl(int(key),4)
        dacl.path='HKCU'+chr(92)+path
        dacl.relative_path=path
        yield dacl
    finally:
        try:
            if dacl:dacl.close()
        finally:
            key.Close()
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER,path)


@contextmanager
def file_fixture():
    path=Path('Deny test '+uuid.uuid4().hex+'.txt').resolve()
    path.write_bytes(b'REAL_READ_WITNESS\n')
    # Open a control-only handle before changing the ACL. This handle does not
    # provide the tested CMD/Python readers with read permission.
    handle=KERNEL.CreateFileW(str(path),0x20000|0x40000,7,None,3,0x80,None)
    if handle==P(-1).value:
        path.unlink();raise C.WinError(C.get_last_error())
    dacl=None
    try:
        dacl=OwnedDacl(handle,1);dacl.path=path
        yield dacl
    finally:
        try:
            if dacl:dacl.close()
        finally:
            KERNEL.CloseHandle(handle)
            path.unlink()
