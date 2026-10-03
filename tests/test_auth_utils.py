import unittest

from backend.utils.authentication import hash_password, verify_password


class AuthUtilsTests(unittest.TestCase):
    def test_hash_and_verify_password(self):
        raw = "SecurePassword123!"
        hashed = hash_password(raw)
        self.assertTrue(hashed.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password(raw, hashed))
        self.assertFalse(verify_password("wrong-password", hashed))


if __name__ == "__main__":
    unittest.main()
