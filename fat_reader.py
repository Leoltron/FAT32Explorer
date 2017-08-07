# !/usr/bin/env python3
from datetime import datetime, date, time, timedelta

import itertools

import fs_objects

BYTES_PER_DIR_ENTRY = 32
BYTES_PER_FAT32_ENTRY = 4


def format_fat_address(address):
    return address & 0x0FFFFFFF


def parse_file_first_cluster_number(entry_parser):
    cluster_number = (entry_parser.parse_int(0 + 20, 2) << 16 + entry_parser.parse_int(0 + 26, 2))
    cluster_number = format_fat_address(cluster_number)
    return cluster_number


def parse_creation_datetime(entry_parser):
    creation_time_millis = entry_parser.parse_int(13, 1)
    creation_datetime = entry_parser.parse_time_date(14)
    creation_datetime += timedelta(milliseconds=creation_time_millis)
    return creation_datetime


def get_lfn_part(entry_bytes):
    utf8_chars_pos = itertools.chain(range(1, 11, 2), range(14, 26, 2), range(28, 32, 2))
    lfn_part = ""
    for pos in utf8_chars_pos:
        char = entry_bytes[pos:pos+2]
        if char != b'\x00\x00' and char != b'\xFF\xFF':
            lfn_part+=char.decode("utf-8")
        else:
            break
    return lfn_part


class Fat32Reader:
    def __init__(self, fat_image):
        self._read_fat32_boot_sector(BytesParser(fat_image))
        self._parse_fat_values(fat_image)

        self.data_area = self.sector_slice(fat_image,
                                           self.reserved_sectors + self.fat_amount * self.sectors_per_fat,
                                           self.total_sectors)

    def _parse_fat_values(self, fat_image):
        active_fat = self.get_active_fat(fat_image)
        fat_parser = BytesParser(active_fat)

        self.fat_values = list()
        for i in range(0, len(active_fat) - BYTES_PER_FAT32_ENTRY, BYTES_PER_FAT32_ENTRY):
            self.fat_values.append(format_fat_address(fat_parser.parse_int(i, BYTES_PER_FAT32_ENTRY)))

    def _read_fat32_boot_sector(self, bytes_parser):
        self._parse_read_boot_sector(bytes_parser)

        self.sectors_per_fat = bytes_parser.parse_int(0x24, 4)
        self.active_fat_number = bytes_parser.parse_int(0x28, 2)

        self.root_catalog_first_cluster_number = bytes_parser.parse_int(0x2c, 4)

        self.boot_sector_copy_sector_number = bytes_parser.parse_int(0x32, 2)

    def _parse_read_boot_sector(self, bytes_parser):
        self.bytes_per_sector = bytes_parser.parse_int(0x0b, 2)
        self.sectors_per_cluster = bytes_parser.parse_int(0x0d, 1)
        self.reserved_sectors = bytes_parser.parse_int(0x0e, 2)
        self.fat_amount = bytes_parser.parse_int(0x10, 1)

        self.total_sectors = bytes_parser.parse_int(0x13, 2)
        self.hidden_sectors_before_partition = bytes_parser.parse_int(0x1c, 4)

        if self.total_sectors == 0:
            self.total_sectors = bytes_parser.parse_int(0x20, 4)

    def sectors_to_bytes(self, sectors):
        return self.bytes_per_sector * sectors

    def sector_slice(self, data, start_sector, end_sector):
        return data[self.sectors_to_bytes(start_sector):self.sectors_to_bytes(end_sector)]

    def cluster_slice(self, data, start_cluster, end_cluster):
        return self.sector_slice(data, start_cluster * self.sectors_per_cluster, end_cluster * self.sectors_per_cluster)

    def get_active_fat(self, fat_image):
        return self.get_fat(fat_image, self.active_fat_number)

    def get_fat(self, fat_image, fat_number):
        start = self.reserved_sectors + fat_number * self.sectors_per_fat
        end = start + self.sectors_per_fat
        return self.sector_slice(fat_image, start, end)

    def get_root_directory(self):
        """
        Возвращает корневой каталог с открываемыми каталоками и файлами.
        """
        return self._parse_dir_files(self.get_data_from_cluster_chain(self.root_catalog_first_cluster_number))

    def _parse_dir_files(self, data):
        files = list()
        long_file_name_buffer = ""
        for i in range(0, len(data) - BYTES_PER_DIR_ENTRY, BYTES_PER_DIR_ENTRY):
            entry_bytes = data[i:i + BYTES_PER_DIR_ENTRY]
            entry_parser = BytesParser(entry_bytes)
            attributes = entry_parser.parse_int(11, 1)
            if attributes == fs_objects.LFN:  # Long file name entry
                long_file_name_buffer = get_lfn_part(entry_bytes) + long_file_name_buffer
            else:
                file = self.parse_file_entry(entry_parser, long_file_name_buffer)
                files.append(file)
                long_file_name_buffer = ""
        return files

    def parse_file_entry(self, entry_parser, long_file_name_buffer):
        attributes = entry_parser.parse_int(11, 1)
        is_directory = attributes & fs_objects.DIRECTORY

        name_part = entry_parser.parse_string(0, 8, "ascii").strip()
        extension_part = entry_parser.parse_string(8, 3, "ascii").strip()
        short_name = name_part + (('.' + extension_part) if not is_directory else "")

        long_name = long_file_name_buffer

        creation_datetime = parse_creation_datetime(entry_parser)

        last_access_date = entry_parser.parse_date(18)
        last_modification_datetime = entry_parser.parse_time_date(22)

        file_size_bytes = entry_parser.parse_int(0 + 28, 4)

        content = self.get_file_content(entry_parser, is_directory)

        return fs_objects.File(short_name,
                               long_name,
                               content,
                               attributes,
                               creation_datetime,
                               last_access_date,
                               last_modification_datetime,
                               file_size_bytes)

    def get_file_content(self, entry_parser, is_directory):
        cluster_number = parse_file_first_cluster_number(entry_parser)
        content = self.get_data_from_cluster_chain(cluster_number)
        if is_directory:
            content = self._parse_dir_files(content)
        return content

    def get_data(self, cluster):
        return self.cluster_slice(self.data_area, cluster, cluster + 1)

    def get_data_from_cluster_chain(self, first_cluster):
        current_cluster = first_cluster
        data = bytes()
        while True:
            data += self.get_data(current_cluster)
            try:
                current_cluster = self.get_next_file_cluster(current_cluster)
            except EOFError:
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

    def parse_int(self, start, length):
        return int.from_bytes(self.byte_arr[start:start + length], byteorder='little', signed=False)

    def parse_string(self, start, length, encoding, errors="strict"):
        return self.byte_arr[start: start + length].decode(encoding=encoding, errors=errors)

    def parse_time(self, start):
        bin_string = bin(self.parse_int(start, 2))

        hour = int(bin_string[0:5], base=2)
        minutes = int(bin_string[5:11], base=2)
        seconds = int(bin_string[11:16], base=2) * 2

        return time(hour=hour, minute=minutes, second=seconds)

    def parse_date(self, start):
        bin_string = bin(self.parse_int(start, 2))

        year = 1980 + int(bin_string[0:7], base=2)
        month = int(bin_string[7:11], base=2)
        day = int(bin_string[11:16], base=2)

        return date(day=day, month=month, year=year)

    def parse_time_date(self, start):
        parsed_time = self.parse_time(start)
        parsed_date = self.parse_date(start + 2)

        return datetime.combine(date=parsed_date, time=parsed_time)
