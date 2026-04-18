import unittest
from unittest import mock

from reverse_ip_checker import check_reverse_ip_domain, validate_ip


class ReverseIpCheckerTests(unittest.TestCase):
    def test_validate_ip_rejects_invalid(self):
        with self.assertRaises(ValueError):
            validate_ip("not-an-ip")

    @mock.patch("reverse_ip_checker.socket.gethostbyname_ex")
    @mock.patch("reverse_ip_checker.socket.gethostbyaddr")
    def test_reverse_and_domain_match(self, mock_reverse, mock_forward):
        mock_reverse.return_value = ("example.com", ["www.example.com"], ["1.2.3.4"])
        mock_forward.return_value = ("example.com", [], ["1.2.3.4", "5.6.7.8"])

        result = check_reverse_ip_domain("1.2.3.4", "example.com")

        self.assertTrue(result["reverse"]["success"])
        self.assertTrue(result["forward"]["success"])
        self.assertTrue(result["forward_matches_ip"])
        self.assertTrue(result["reverse_matches_domain"])

    @mock.patch("reverse_ip_checker.socket.gethostbyaddr")
    def test_reverse_failure(self, mock_reverse):
        mock_reverse.side_effect = OSError("lookup failed")

        result = check_reverse_ip_domain("1.2.3.4")

        self.assertFalse(result["reverse"]["success"])
        self.assertIn("lookup failed", result["reverse"]["error"])


if __name__ == "__main__":
    unittest.main()
