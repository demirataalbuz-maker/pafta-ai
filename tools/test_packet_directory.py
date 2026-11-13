"""Native dissector field and encrypted-transform regression."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sandbox import packet_engine as e


class DirectoryPackets(unittest.TestCase):
    def test_smb_direction_status_and_encrypted_absence(self):
        self.assertEqual(e.evaluate('smb2.cmd == 3 and smb2.flags.response == 0','smb-lab'),[6,8,10])
        self.assertEqual(e.evaluate('smb2.nt_status == 0xc0000022','smb-lab'),[9])
        self.assertEqual(e.evaluate('smb2.header.transform.flags.encrypted','smb-lab'),[12])
        self.assertNotIn(12,e.evaluate('smb2.cmd','smb-lab'))

    def test_kerberos_message_identity_and_error_neighbours(self):
        self.assertEqual(e.evaluate('kerberos.msg_type == 10','kerberos-lab'),[1,5])
        self.assertEqual(e.evaluate('kerberos.msg_type == 10 and kerberos.CNameString == "alice"','kerberos-lab'),[1])
        for code,expected in ((23,[2]),(24,[3]),(25,[4])):
            self.assertEqual(e.evaluate(f'kerberos.error_code == {code}','kerberos-lab'),expected)

    def test_ldap_bind_and_search_result_fields_differ(self):
        for code,expected in ((0,[5]),(48,[7]),(49,[9]),(50,[11])):
            self.assertEqual(e.evaluate(f'ldap.bindResponse_resultCode == {code}','ldap-lab'),expected)
        self.assertEqual(e.evaluate('ldap.resultCode == 0','ldap-lab'),[13,15])
        self.assertEqual(e.evaluate('ldap.baseObject == "DC=lab,DC=test"','ldap-lab'),[12])


if __name__=='__main__':unittest.main(verbosity=2)
