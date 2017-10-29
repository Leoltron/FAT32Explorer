# !/usr/bin/env python3
import datetime
import unittest

import directory_browser
import fat_reader
import fs_objects
from bytes_parsers import FileBytesParser

ASCII = "ascii"
UTF16 = "utf16"


def generate_files_from_names(names):
    for name in names:
        yield fs_objects.File("", name)


class FileTests(unittest.TestCase):
    def test_get_absolute_path(self):
        root = fs_objects.File("root", "root", fs_objects.DIRECTORY)
        self.assertEqual(root.get_absolute_path(), "root")

        folder1 = fs_objects.File("Folder1", "Folder1", fs_objects.DIRECTORY)
        folder1.parent = root
        self.assertEqual(folder1.get_absolute_path(), "root/Folder1")

        folder2 = fs_objects.File("Folder2", "Folder2", fs_objects.DIRECTORY)
        folder2.parent = folder1
        self.assertEqual(folder2.get_absolute_path(), "root/Folder1/Folder2")

    def test_size_format_byte(self):
        file = fs_objects.File("file", "file", size_bytes=1)
        self.assertEqual("1 byte", file.get_size_str())

    def test_size_format_bytes(self):
        file = fs_objects.File("file", "file", size_bytes=5)
        self.assertEqual("5 bytes", file.get_size_str())

    def test_size_format_kibibytes(self):
        file = fs_objects.File("file", "file", size_bytes=855310)
        self.assertEqual("835.26 KiB (855310 bytes)", file.get_size_str())

    def test_size_format_mebibytes(self):
        file = fs_objects.File("file", "file", size_bytes=6389353)
        self.assertEqual("6.09 MiB (6389353 bytes)", file.get_size_str())

    def test_size_format_gibibytes(self):
        file = fs_objects.File("file", "file", size_bytes=281382002220)
        self.assertEqual("262.06 GiB (281382002220 bytes)",
                         file.get_size_str())

    def test_attr_str_full(self):
        file = fs_objects.File("file", "file",
                               fs_objects.READ_ONLY |
                               fs_objects.HIDDEN |
                               fs_objects.SYSTEM |
                               fs_objects.VOLUME_ID |
                               fs_objects.DIRECTORY |
                               fs_objects.ARCHIVE)
        self.assertEqual("read_only, hidden, system, "
                         "volume_id, directory, archive"
                         , file.get_attributes_str())

    def test_attr_str_part(self):
        file = fs_objects.File("file", "file",
                               fs_objects.READ_ONLY |
                               fs_objects.HIDDEN |
                               fs_objects.ARCHIVE)
        self.assertEqual("read_only, hidden, archive",
                         file.get_attributes_str())

    def test_attr_str_empty(self):
        file = fs_objects.File("file", "file")
        self.assertEqual("", file.get_attributes_str())


class BytesParserTests(unittest.TestCase):
    def test_parse_int_simple(self):
        parser = FileBytesParser(b'\x5f')
        self.assertEqual(0x5f, parser.parse_int_unsigned(0, 1))

    def test_parse_int_little_big_endian(self):
        parser = FileBytesParser(b'\xf4\xa3\xff')
        self.assertEqual(0xffa3f4, parser.parse_int_unsigned(0, 3))

    def test_parse_int_start(self):
        parser = FileBytesParser(b'\xf4\x43\xff\x57\xa3\x55')
        self.assertEqual(0xff43f4, parser.parse_int_unsigned(0, 3))

    def test_parse_int_middle(self):
        parser = FileBytesParser(b'\xf4\x43\xff\x57\xa3\x55')
        self.assertEqual(0x57ff, parser.parse_int_unsigned(2, 2))

    def test_parse_int_end(self):
        parser = FileBytesParser(b'\xf4\x43\xff\x57\xa3\x55')
        self.assertEqual(0x55, parser.parse_int_unsigned(5, 1))

    def test_parse_string_start(self):
        parser = FileBytesParser("Я love Python".encode(encoding=UTF16))
        self.assertEqual("Я love", parser.parse_string(0, 14, encoding=UTF16))

    def test_parse_string_middle(self):
        parser = FileBytesParser("I love Python".encode(encoding=ASCII))
        self.assertEqual("love", parser.parse_string(2, 4, encoding=ASCII))

    def test_parse_string_end(self):
        parser = FileBytesParser("Hello, world!".encode(encoding=ASCII))
        self.assertEqual("world!", parser.parse_string(7, 6, encoding=ASCII))

    def test_parse_time_start(self):  # 1:25:00
        # [0010000000001011]
        parser = FileBytesParser(b'\x20\x0b')
        self.assertEqual(datetime.time(hour=1, minute=25, second=0),
                         parser.parse_time(0))

    def test_parse_time_middle(self):  # 1:25:00
        # 00001111[1000011001100001]1010111100000000
        parser = FileBytesParser(b'\x0F\x86\x61\xAF\x00')
        self.assertEqual(datetime.time(hour=12, minute=12, second=12),
                         parser.parse_time(1))

    def test_parse_time_end(self):  # 17:35:54
        # 0000101100101000[0111101110001100]
        parser = FileBytesParser(b'\x0B\x28\x7B\x8C')
        self.assertEqual(datetime.time(hour=17, minute=35, second=54),
                         parser.parse_time(2))

    def test_parse_date_start(self):  # 09.08.2017(37) -> 37 08 09
        # [0000100101001011]00000000
        parser = FileBytesParser(b'\x09\x4B\x00')
        self.assertEqual(datetime.date(year=2017, month=8, day=9),
                         parser.parse_date(0))

    def test_parse_date_middle(self):  # 08.10.1998(18) -> 18 10 08
        # 110110000000101010000000[0010010101001000]10101011
        parser = FileBytesParser(b'\xd8\x0a\x80\x48\x25\xab')
        self.assertEqual(datetime.date(year=1998, month=10, day=8),
                         parser.parse_date(3))

    def test_parse_date_end(self):  # 01.01.2000(20) -> 20 01 01
        # 10111011110001101101010101010000010111[0010000100101000]
        parser = FileBytesParser(b'\x2e\xf1\xb5\x54\x17\x21\x28')
        self.assertEqual(datetime.date(year=2000, month=1, day=1),
                         parser.parse_date(5))


class FatReaderStaticTests(unittest.TestCase):
    def test_file_parse(self):
        file_expected = fs_objects.File('SHORT.TXT', '', fs_objects.ARCHIVE,
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

        parser = FileBytesParser(
            b'\x53\x48\x4F\x52\x54\x20\x20\x20\x54\x58\x54\x20\x18\x4C\xA8\x76'
            b'\xFD\x4A\xFD\x4A\x00\x00\x05\xA3\xEE\x4A\x55\x00\xA3\x06\x00\x00'
        )
        file_actual = fat_reader.parse_file_info(parser)
        self.assertEqual(file_actual, file_expected)

    def test_lfn_part(self):
        lfn_bytes = b'\x43\x38\x04\x38\x04\x2E\x00\x74\x00\x78\x00' \
                    b'\x0F\x00\x31\x74\x00\x00\x00\xFF\xFF\xFF\xFF' \
                    b'\xFF\xFF\xFF\xFF\x00\x00\xFF\xFF\xFF\xFF'
        self.assertEqual(fat_reader.get_lfn_part(lfn_bytes),
                         "ии.txt")


class FatReaderTests(unittest.TestCase):
    # noinspection SpellCheckingInspection
    def test_image(self):
        fi = open("TEST-IMAGE", "rb")
        try:
            f = fat_reader.Fat32Reader(fi.read())
        finally:
            fi.close()
        names = f.get_root_directory().get_dir_hierarchy()
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


class DirectoryBrowserTests(unittest.TestCase):
    def test_get_dir_content_names(self):
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d = fs_objects.File("DIR", "",
                            fs_objects.DIRECTORY)
        d.content = list(generate_files_from_names(names))
        self.assertEqual(list(directory_browser._get_dir_content_names(d)),
                         names)

    def test_get_dir_content_names_empty_dir(self):
        d = fs_objects.File("DIR", "",
                            fs_objects.DIRECTORY)
        d.content = []
        self.assertEqual(list(directory_browser._get_dir_content_names(d)), [])

    def test_get_dir_content_names_not_a_dir(self):
        file = fs_objects.File("", "File.txt")
        with self.assertRaises(NotADirectoryError):
            list(directory_browser._get_dir_content_names(file))

    def test_cd(self):
        d = fs_objects.File("DIR", "", fs_objects.DIRECTORY)
        d1 = fs_objects.File("DIR1", "", fs_objects.DIRECTORY)
        d.content = [d1]
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d1.content = list(generate_files_from_names(names))

        db = directory_browser.DirectoryBrowser(d)
        db.change_directory("DIR1")

        self.assertEqual(db.current, d1)

    def test_cd_fail_not_found(self):
        d = fs_objects.File("DIR", "", fs_objects.DIRECTORY)
        d1 = fs_objects.File("DIR1", "", fs_objects.DIRECTORY)
        d.content = [d1]
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d1.content = list(generate_files_from_names(names))

        db = directory_browser.DirectoryBrowser(d)

        with self.assertRaises(directory_browser.DirectoryBrowserError):
            db.change_directory("dir")

    def test_cd_fail_not_a_directory(self):
        d = fs_objects.File("DIR", "", fs_objects.DIRECTORY)
        d1 = fs_objects.File("DIR1", "", fs_objects.DIRECTORY)
        d.content = [d1]
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d1.content = list(generate_files_from_names(names))

        db = directory_browser.DirectoryBrowser(d)

        with self.assertRaises(directory_browser.DirectoryBrowserError):
            db.change_directory("DIR1/File1.txt")

    def test_cd_deep(self):
        d_root = fs_objects.File("DIR", "", fs_objects.DIRECTORY)
        d = fs_objects.File("DIR1", "", fs_objects.DIRECTORY)
        d1 = fs_objects.File("DIR2", "", fs_objects.DIRECTORY)
        d_root.content = [d]
        d.content = [d1]
        names = ["File1.txt", "File2.txt", "File3.txt"]
        d1.content = list(generate_files_from_names(names))

        db = directory_browser.DirectoryBrowser(d_root)
        db.change_directory("DIR1/DIR2")

        self.assertEqual(db.current, d1)


if __name__ == '__main__':
    unittest.main()
