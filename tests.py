# !/usr/bin/env python3
import datetime
import unittest

from pathlib import Path

import os

import dirbrowser
import fateditor
import fsobjects
from bytes_parsers import BytesParser

TEST_IMAGE_ARCHIVE_URL = "https://github.com/Leoltron/FAT32Explorer/raw/master/TEST-IMAGE.zip"

ASCII = "ascii"
UTF16 = "utf16"


def generate_files_from_names(names):
    for name in names:
        yield fsobjects.File("", name)


class FileTests(unittest.TestCase):
    def test_get_absolute_path(self):
        root = fsobjects.File("root", "root", fsobjects.DIRECTORY)
        self.assertEqual(root.get_absolute_path(), "root")

        folder1 = fsobjects.File("Folder1", "Folder1", fsobjects.DIRECTORY)
        folder1.parent = root
        self.assertEqual(folder1.get_absolute_path(), "root/Folder1")

        folder2 = fsobjects.File("Folder2", "Folder2", fsobjects.DIRECTORY)
        folder2.parent = folder1
        self.assertEqual(folder2.get_absolute_path(), "root/Folder1/Folder2")

    def test_size_format_byte(self):
        file = fsobjects.File("file", "file", size_bytes=1)
        self.assertEqual("1 byte", file.get_size_str())

    def test_size_format_bytes(self):
        file = fsobjects.File("file", "file", size_bytes=5)
        self.assertEqual("5 bytes", file.get_size_str())

    def test_size_format_kibibytes(self):
        file = fsobjects.File("file", "file", size_bytes=855310)
        self.assertEqual("835.26 KiB (855310 bytes)", file.get_size_str())

    def test_size_format_mebibytes(self):
        file = fsobjects.File("file", "file", size_bytes=6389353)
        self.assertEqual("6.09 MiB (6389353 bytes)", file.get_size_str())

    def test_size_format_gibibytes(self):
        file = fsobjects.File("file", "file", size_bytes=281382002220)
        self.assertEqual("262.06 GiB (281382002220 bytes)",
                         file.get_size_str())

    def test_attr_str_full(self):
        file = fsobjects.File("file", "file",
                              fsobjects.READ_ONLY |
                              fsobjects.HIDDEN |
                              fsobjects.SYSTEM |
                              fsobjects.VOLUME_ID |
                              fsobjects.DIRECTORY |
                              fsobjects.ARCHIVE)
        self.assertEqual("read_only, hidden, system, "
                         "volume_id, directory, archive"
                         , file.get_attributes_str())

    def test_attr_str_part(self):
        file = fsobjects.File("file", "file",
                              fsobjects.READ_ONLY |
                              fsobjects.HIDDEN |
                              fsobjects.ARCHIVE)
        self.assertEqual("read_only, hidden, archive",
                         file.get_attributes_str())

    def test_attr_str_empty(self):
        file = fsobjects.File("file", "file")
        self.assertEqual("no attributes", file.get_attributes_str())


class BytesParserTests(unittest.TestCase):
    def test_parse_int_simple(self):
        parser = BytesParser(b'\x5f')
        self.assertEqual(0x5f, parser.parse_int_unsigned(0, 1))

    def test_parse_int_little_big_endian(self):
        parser = BytesParser(b'\xf4\xa3\xff')
        self.assertEqual(0xffa3f4, parser.parse_int_unsigned(0, 3))

    def test_parse_int_start(self):
        parser = BytesParser(b'\xf4\x43\xff\x57\xa3\x55')
        self.assertEqual(0xff43f4, parser.parse_int_unsigned(0, 3))

    def test_parse_int_middle(self):
        parser = BytesParser(b'\xf4\x43\xff\x57\xa3\x55')
        self.assertEqual(0x57ff, parser.parse_int_unsigned(2, 2))

    def test_parse_int_end(self):
        parser = BytesParser(b'\xf4\x43\xff\x57\xa3\x55')
        self.assertEqual(0x55, parser.parse_int_unsigned(5, 1))

    def test_parse_string_start(self):
        parser = BytesParser("Я love Python".encode(encoding=UTF16))
        self.assertEqual("Я love", parser.parse_string(0, 14, encoding=UTF16))

    def test_parse_string_middle(self):
        parser = BytesParser("I love Python".encode(encoding=ASCII))
        self.assertEqual("love", parser.parse_string(2, 4, encoding=ASCII))

    def test_parse_string_end(self):
        parser = BytesParser("Hello, world!".encode(encoding=ASCII))
        self.assertEqual("world!", parser.parse_string(7, 6, encoding=ASCII))

    def test_parse_time_start(self):  # 1:25:00
        # [0010000000001011]
        parser = BytesParser(b'\x20\x0b')
        self.assertEqual(datetime.time(hour=1, minute=25, second=0),
                         parser.parse_time(0))

    def test_parse_time_middle(self):  # 1:25:00
        # 00001111[1000011001100001]1010111100000000
        parser = BytesParser(b'\x0F\x86\x61\xAF\x00')
        self.assertEqual(datetime.time(hour=12, minute=12, second=12),
                         parser.parse_time(1))

    def test_parse_time_end(self):  # 17:35:54
        # 0000101100101000[0111101110001100]
        parser = BytesParser(b'\x0B\x28\x7B\x8C')
        self.assertEqual(datetime.time(hour=17, minute=35, second=54),
                         parser.parse_time(2))

    def test_parse_date_start(self):  # 09.08.2017(37) -> 37 08 09
        # [0000100101001011]00000000
        parser = BytesParser(b'\x09\x4B\x00')
        self.assertEqual(datetime.date(year=2017, month=8, day=9),
                         parser.parse_date(0))

    def test_parse_date_middle(self):  # 08.10.1998(18) -> 18 10 08
        # 110110000000101010000000[0010010101001000]10101011
        parser = BytesParser(b'\xd8\x0a\x80\x48\x25\xab')
        self.assertEqual(datetime.date(year=1998, month=10, day=8),
                         parser.parse_date(3))

    def test_parse_date_end(self):  # 01.01.2000(20) -> 20 01 01
        # 10111011110001101101010101010000010111[0010000100101000]
        parser = BytesParser(b'\x2e\xf1\xb5\x54\x17\x21\x28')
        self.assertEqual(datetime.date(year=2000, month=1, day=1),
                         parser.parse_date(5))


class FatReaderStaticTests(unittest.TestCase):
    def test_file_parse(self):
        file_expected = fsobjects.File('SHORT.TXT', '', fsobjects.ARCHIVE,
                                       datetime.datetime(day=29, month=7,
                                                         year=2017, hour=14,
                                                         minute=53, second=16,
                                                         microsecond=76000),
                                       datetime.date(day=29, month=7,
                                                     year=2017),
                                       datetime.datetime(day=14, month=7,
                                                         year=2017, hour=20,
                                                         minute=24,
                                                         second=10),
                                       1699)

        parser = BytesParser(
            b'\x53\x48\x4F\x52\x54\x20\x20\x20\x54\x58\x54\x20\x18\x4C\xA8\x76'
            b'\xFD\x4A\xFD\x4A\x00\x00\x05\xA3\xEE\x4A\x55\x00\xA3\x06\x00\x00'
        )
        file_actual = fateditor.parse_file_info(parser)
        self.assertEqual(file_actual, file_expected)

    def test_lfn_part(self):
        lfn_bytes = b'\x43\x38\x04\x38\x04\x2E\x00\x74\x00\x78\x00' \
                    b'\x0F\x00\x31\x74\x00\x00\x00\xFF\xFF\xFF\xFF' \
                    b'\xFF\xFF\xFF\xFF\x00\x00\xFF\xFF\xFF\xFF'
        self.assertEqual(fateditor.get_lfn_part(lfn_bytes)[0],
                         "ии.txt")


TEST_IMAGE_NAME = "TEST-IMAGE"
TESTS_RES_DIR_NAME = "tests_tmp_resources"


def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


class FatReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path_str = get_test_image_path()
        ensure_dir(path_str)
        zip_path_str = get_test_image_path() + ".zip"

        if os.path.exists(path_str):
            os.remove(path_str)
        if os.path.exists(zip_path_str):
            os.remove(zip_path_str)

        print("Downloading TEST-IMAGE.zip...")
        from urllib import request
        request.urlretrieve(TEST_IMAGE_ARCHIVE_URL, zip_path_str)
        print("Download complete.")

        print("Extracting test images... ", end='')
        import zipfile
        with zipfile.ZipFile(zip_path_str, "r") as zip_ref:
            zip_ref.extractall(TESTS_RES_DIR_NAME)
        print("Done.")

    # noinspection SpellCheckingInspection
    def test_image(self):
        with open(get_test_image_path(), "rb") as fi:
            f = fateditor.Fat32Editor(fi, silent_scan=True)
            self.assert_test_image(f)

    def test_image_corrupted(self):
        with open(get_test_image_path() + "-CORRUPTED", "r+b") as fi:
            f = fateditor.Fat32Editor(fi, True, silent_scan=True)
            f.scandisk(True, True, True)
            self.assert_test_image(f)

    def assert_test_image(self, test_image_file):
        names = test_image_file.get_root_directory().get_dir_hierarchy()
        self.assertEqual(names,
                         {
                             "System Volume Information": {
                                 "WPSettings.dat": {},
                                 "IndexerVolumeGuid": {}},
                             "Folder1": {"Astaf.txt": {}, "SHORT.TXT": {}},
                             "Файл.txt": {},
                             "FileQWERTYUIOPASDFGHJKLZXCVBNMAZQWSXEDCRF"
                             "VTGBYHNUJMIKZAWSXEDCRGBY"
                             "HUJNMZQAWSXEDCRTGBYHNUJMIK.txt": {},
                             "VXlZSvgG0z0.jpg": {},
                             "Файл с кириллицей в названии.txt": {},
                             "$RECYCLE": {"DESKTOP.INI": {}}, }
                         )

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(TESTS_RES_DIR_NAME)


def get_test_image_path():
    return TESTS_RES_DIR_NAME + "/" + TEST_IMAGE_NAME


class DirectoryBrowserTests(unittest.TestCase):
    def test_get_dir_content_names(self):
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d = fsobjects.File("DIR", "",
                           fsobjects.DIRECTORY)
        d.content = list(generate_files_from_names(names))
        self.assertEqual(list(dirbrowser._get_dir_content_names(d)),
                         names)

    def test_get_dir_content_names_empty_dir(self):
        d = fsobjects.File("DIR", "",
                           fsobjects.DIRECTORY)
        d.content = []
        self.assertEqual(list(dirbrowser._get_dir_content_names(d)), [])

    def test_get_dir_content_names_not_a_dir(self):
        file = fsobjects.File("", "File.txt")
        with self.assertRaises(NotADirectoryError):
            list(dirbrowser._get_dir_content_names(file))

    def test_cd(self):
        d = fsobjects.File("DIR", "", fsobjects.DIRECTORY)
        d1 = fsobjects.File("DIR1", "", fsobjects.DIRECTORY)
        d.content = [d1]
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d1.content = list(generate_files_from_names(names))

        db = dirbrowser.DirectoryBrowser(root=d)
        db.change_directory("DIR1")

        self.assertEqual(db.current, d1)

    def test_cd_fail_not_found(self):
        d = fsobjects.File("DIR", "", fsobjects.DIRECTORY)
        d1 = fsobjects.File("DIR1", "", fsobjects.DIRECTORY)
        d.content = [d1]
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d1.content = list(generate_files_from_names(names))

        db = dirbrowser.DirectoryBrowser(root=d)

        with self.assertRaises(dirbrowser.DirectoryBrowserError):
            db.change_directory("dir")

    def test_cd_fail_not_a_directory(self):
        d = fsobjects.File("DIR", "", fsobjects.DIRECTORY)
        d1 = fsobjects.File("DIR1", "", fsobjects.DIRECTORY)
        d.content = [d1]
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d1.content = list(generate_files_from_names(names))

        db = dirbrowser.DirectoryBrowser(root=d)

        with self.assertRaises(dirbrowser.DirectoryBrowserError):
            db.change_directory("DIR1/File1.txt")

    def test_cd_deep(self):
        d_root = fsobjects.File("DIR", "", fsobjects.DIRECTORY)
        d = fsobjects.File("DIR1", "", fsobjects.DIRECTORY)
        d1 = fsobjects.File("DIR2", "", fsobjects.DIRECTORY)
        d_root.content = [d]
        d.content = [d1]
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d1.content = list(generate_files_from_names(names))

        db = dirbrowser.DirectoryBrowser(root=d_root)
        db.change_directory("DIR1/DIR2")

        self.assertEqual(db.current, d1)


class WriterTests(unittest.TestCase):
    def test_lfn_encoding(self):
        name = "qwertyuioiuhgfdsxdcfgtDASDASDAdd12312312.png"
        parts = fsobjects.to_lfn_parts(name)
        actual = ""
        for part in parts:
            actual = fateditor.get_lfn_part(part)[0] + actual
        self.assertEqual(actual, name)

    def test_turn_short(self):
        name = "qwertyuioiuhgfdsxdcfgtDASDASDAdd12312312.png"
        short_name = fsobjects.get_short_name(name, None)
        self.assertEqual(short_name, "QWERTY~1.PNG")


if __name__ == '__main__':
    unittest.main()
