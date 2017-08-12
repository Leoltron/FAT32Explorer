# !/usr/bin/env python3
from datetime import datetime, date, time, timedelta

import itertools
import fs_objects

from main import debug

BYTES_PER_DIR_ENTRY = 32
BYTES_PER_FAT32_ENTRY = 4


def format_fat_address(address):
    return address & 0x0FFFFFFF


def parse_file_first_cluster_number(entry_parser):
    cluster_number = (entry_parser.parse_int_unsigned(0 + 20, 2) << 16 + entry_parser.parse_int_unsigned(0 + 26, 2))
    cluster_number = format_fat_address(cluster_number)
    return cluster_number


def parse_creation_datetime(entry_parser):
    creation_time_millis = entry_parser.parse_int_unsigned(13, 1)
    creation_datetime = entry_parser.parse_time_date(14)
    creation_datetime += timedelta(milliseconds=creation_time_millis)
    return creation_datetime


def get_lfn_part(entry_bytes):
    utf8_chars_pos = itertools.chain(range(1, 11, 2), range(14, 26, 2), range(28, 32, 2))
    lfn_part = ""
    for pos in utf8_chars_pos:
        char = entry_bytes[pos:pos + 2]
        if char != b'\x00\x00' and char != b'\xFF\xFF':
            lfn_part += char.decode("utf-8")
        else:
            break
    return lfn_part


def parse_file_info(entry_parser, long_file_name_buffer=""):
    attributes = entry_parser.parse_int_unsigned(11, 1)
    is_directory = bool(attributes & fs_objects.DIRECTORY)

    name_part = entry_parser.parse_string(0, 8, "ascii", "strict").strip()
    extension_part = entry_parser.parse_string(8, 3, "ascii", "strict").strip()
    short_name = name_part + (('.' + extension_part) if not is_directory else "")
    debug("\tshort_name: " + short_name)

    creation_datetime = parse_creation_datetime(entry_parser)

    last_access_date = entry_parser.parse_date(18)
    last_modification_datetime = entry_parser.parse_time_date(22)

    file_size_bytes = entry_parser.parse_int_unsigned(0 + 28, 4)

    return fs_objects.File(short_name,
                           long_file_name_buffer,
                           None,
                           attributes,
                           creation_datetime,
                           last_access_date,
                           last_modification_datetime,
                           file_size_bytes)


class Fat32Reader:
    def __init__(self, fat_image):
        self._read_fat32_boot_sector(BytesParser(fat_image))
        self._parse_fat_values(fat_image)
        self._parse_data_area(fat_image)

    def _parse_fat_values(self, fat_image):
        active_fat = self._get_active_fat(fat_image)
        fat_parser = BytesParser(active_fat)

        self.fat_values = list()
        for i in range(0, len(active_fat) - BYTES_PER_FAT32_ENTRY, BYTES_PER_FAT32_ENTRY):
            self.fat_values.append(format_fat_address(fat_parser.parse_int_unsigned(i, BYTES_PER_FAT32_ENTRY)))

    def _parse_data_area(self, fat_image):
        start = self._sectors_to_bytes(self.reserved_sectors + self.fat_amount * self.sectors_per_fat)
        self.data = list()
        bytes_per_cluster = self.bytes_per_sector * self.sectors_per_cluster
        for cluster_start in range(start, len(fat_image) - bytes_per_cluster, bytes_per_cluster):
            self.data.append(fat_image[cluster_start:cluster_start + bytes_per_cluster])

    def _read_fat32_boot_sector(self, bytes_parser):
        self._parse_read_boot_sector(bytes_parser)

        self.sectors_per_fat = bytes_parser.parse_int_unsigned(0x24, 4)
        self.active_fat_number = bytes_parser.parse_int_unsigned(0x28, 2)

        self.root_catalog_first_cluster_number = bytes_parser.parse_int_unsigned(0x2c, 4)

        self.boot_sector_copy_sector_number = bytes_parser.parse_int_unsigned(0x32, 2)

    def _parse_read_boot_sector(self, bytes_parser):
        self.bytes_per_sector = bytes_parser.parse_int_unsigned(0x0b, 2)
        self.sectors_per_cluster = bytes_parser.parse_int_unsigned(0x0d, 1)
        self.reserved_sectors = bytes_parser.parse_int_unsigned(0x0e, 2)
        self.fat_amount = bytes_parser.parse_int_unsigned(0x10, 1)

        self.total_sectors = bytes_parser.parse_int_unsigned(0x13, 2)
        self.hidden_sectors_before_partition = bytes_parser.parse_int_unsigned(0x1c, 4)

        if self.total_sectors == 0:
            self.total_sectors = bytes_parser.parse_int_unsigned(0x20, 4)

    def _sectors_to_bytes(self, sectors):
        return self.bytes_per_sector * sectors

    def _sector_slice(self, data, start_sector, end_sector=None):
        if end_sector is None:
            return data[self._sectors_to_bytes(start_sector)]
        else:
            return data[self._sectors_to_bytes(start_sector):self._sectors_to_bytes(end_sector)]

    def _cluster_slice(self, data, start_cluster, end_cluster):
        return self._sector_slice(data, start_cluster * self.sectors_per_cluster,
                                  end_cluster * self.sectors_per_cluster)

    def _get_active_fat(self, fat_image):
        return self._get_fat(fat_image, self.active_fat_number)

    def _get_fat(self, fat_image, fat_number):
        start = self.reserved_sectors + fat_number * self.sectors_per_fat
        end = start + self.sectors_per_fat
        return self._sector_slice(fat_image, start, end)

    def get_root_directory(self):
        """
        Возвращает корневой каталог с открываемыми каталогами и файлами.
        """
        return self._parse_dir_files(self.get_data_from_cluster_chain(self.root_catalog_first_cluster_number))

    def _parse_dir_files(self, data):
        files = list()
        long_file_name_buffer = ""
        for start in range(0, len(data) - BYTES_PER_DIR_ENTRY, BYTES_PER_DIR_ENTRY):
            entry_bytes = data[start:start + BYTES_PER_DIR_ENTRY]
            if entry_bytes[0] == b'\x05' or entry_bytes[0] == b'\xE5':
                continue
            entry_parser = BytesParser(entry_bytes)
            attributes = entry_parser.parse_int_unsigned(11, 1)
            if attributes == fs_objects.LFN:  # Long file name entry
                long_file_name_buffer = get_lfn_part(entry_bytes) + long_file_name_buffer
            else:
                file = self._parse_file_entry(entry_parser, long_file_name_buffer)
                files.append(file)
                long_file_name_buffer = ""
        return files

    def _parse_file_entry(self, entry_parser, long_file_name_buffer):
        debug("parse_file_entry: ")
        debug("\thex: " + entry_parser.hex_readable(0, BYTES_PER_DIR_ENTRY))

        file = parse_file_info(entry_parser, long_file_name_buffer)
        file.content = self._get_file_content(entry_parser, file.is_directory)

        return file

    def _get_file_content(self, entry_parser, is_directory):
        first_cluster = parse_file_first_cluster_number(entry_parser)
        content = self.get_data_from_cluster_chain(first_cluster)
        if is_directory:
            content = self._parse_dir_files(content)
        return content

    def get_data(self, cluster):
        return self.data[cluster-2]

    def get_data_from_cluster_chain(self, first_cluster):
        current_cluster = first_cluster
        data = bytes()
        cluster_chain = str(first_cluster)
        while True:
            data += self.get_data(current_cluster)
            try:
                current_cluster = self.get_next_file_cluster(current_cluster)
                cluster_chain += "-" + str(current_cluster)
            except EOFError:
                debug("Cluster chain: "+cluster_chain)
                return data

    def get_next_file_cluster(self, prev_cluster):
        table_value = self.fat_values[prev_cluster]
        if table_value < 0x0FFFFFF7:
            return table_value
        else:
            raise EOFError


class BytesParser:
    def __init__(self, byte_arr):
        self.byte_arr = byte_arr

    def parse_int_unsigned(self, start, length, byteorder='little'):
        return int.from_bytes(self.byte_arr[start:start + length], byteorder=byteorder, signed=False)

    def parse_string(self, start, length, encoding, errors="strict"):
        return self.byte_arr[start: start + length].decode(encoding=encoding, errors=errors)

    def parse_time_date(self, start):
        parsed_time = self.parse_time(start)
        parsed_date = self.parse_date(start + 2)

        return datetime.combine(date=parsed_date, time=parsed_time)

    def parse_time(self, start):
        bin_string = self.parse_bin_str(start, 2)

        debug("parse_time: " + bin_string)
        debug("hour: " + bin_string[0:5])
        debug("minutes: " + bin_string[5:11])
        debug("seconds: " + bin_string[11:16])

        hour = int(bin_string[0:5], base=2)
        minutes = int(bin_string[5:11], base=2)
        seconds = int(bin_string[11:16], base=2) * 2

        return time(hour=hour, minute=minutes, second=seconds)

    def parse_date(self, start):
        bin_string = self.parse_bin_str(start, 2)

        debug("parse_date: " + bin_string)
        debug("\ty: " + bin_string[:7])
        debug("\tm: " + bin_string[7:11])
        debug("\td: " + bin_string[11:16])

        year = 1980 + int(bin_string[:7], base=2)
        month = int(bin_string[7:11], base=2)
        day = int(bin_string[11:16], base=2)

        return date(day=day, month=month, year=year)

    def parse_bin_str(self, start_byte, length_bytes):
        return bin(self.parse_int_unsigned(start_byte, length_bytes, byteorder="little"))[2:].zfill(8 * length_bytes)

    def hex_readable(self, start, length):
        import binascii
        h = str(binascii.hexlify(self.byte_arr[start: start + length]))[2:-1].upper()
        return ' '.join(a + b for a, b in zip(h[::2], h[1::2]))
