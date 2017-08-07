# !/usr/bin/env python3

import unittest
import main


class Test(unittest.TestCase):
    def test_get_int_lbe(self):
        arr = [0, 0, 0, 0b11001101, 0b10101011, 0, 0, 0, 0]

        self.assertEqual(43981, main.bytes_to_int_lbe(arr, 3, 2))

    def test_get_int_ble(self):
        arr = [0, 0, 0, 0b10101011, 0b11001101, 0, 0, 0, 0]

        self.assertEqual(43981, main.bytes_to_int_ble(arr, 3, 2))
