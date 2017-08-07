# !/usr/bin/env python3
from datetime import datetime, date, time, timedelta

import fs_objects

class Fat32:
    def __init__(self, byte_arr):
        self._bytes = byte_arr
        self._parse_fat32_boot_sector()

    def _parse_fat32_boot_sector(self):
        self._parse_fat_boot_sector()

        self.sectors_per_fat = self.parse_int(0x24, 4)
        self.active_fat_number = self.parse_int(0x28, 2)

        self.fat_version = self.parse_int(0x2a, 2)
        self.root_catalog_first_cluster_number = self.parse_int(0x2c, 4)
        self.fs_info_sector_number = self.parse_int(0x30, 2)

        self.boot_sector_copy_sector_number = self.parse_int(0x32, 2)

    def _parse_fat_boot_sector(self):
        self.jump = self.parse_int(0x0, 3)
        self.oem_id = self.parse_string(0x03, 8, "ascii")
        self.bytes_per_sector = self.parse_int(0x0b, 2)
        self.sectors_per_cluster = self.parse_int(0x0d, 1)
        self.reserved_sectors = self.parse_int(0x0e, 2)
        self.fat_amount = self.parse_int(0x10, 1)

        self.total_sectors = self.parse_int(0x13, 2)
        self.hidden_sectors_before_partition = self.parse_int(0x1c, 4)

        if self.total_sectors == 0:
            self.total_sectors = self.parse_int(0x20, 4)

    def get_bytes(self):
        return self._bytes

    def sectors_to_bytes(self, sectors):
        return self.bytes_per_sector * sectors

    def get_sector_slice(self, start_sector, end_sector):
        return self._bytes[self.sectors_to_bytes(start_sector):
        self.sectors_to_bytes(end_sector)]

    @property
    def active_fat(self):
        return self.get_fat(self.active_fat_number)

    def get_fat(self, fat_number):
        start = self.reserved_sectors
        start += fat_number * self.sectors_per_fat
        end = start + self.sectors_per_fat
        return self.get_sector_slice(start, end)

    def get_content(self, cluster_number):
        content = self.sectors_to_bytes(self.get_data_area_start_sector() + self.sectors_per_cluster * cluster_number)
        next_cluster_number = self.get_fat_entry_value(cluster_number)
        next_cluster_number = next_cluster_number & 0b0000111111111111  # Removing unused in FAT32 address 4 highest bits
        if next_cluster_number < 0x0FFFFFF7:
            content += self.get_content(next_cluster_number)
        return content

    def get_fat_entry_value(self, number):
        return self.active_fat[number * 32:number * 32 + 32]

    def get_root_dir_start_sector(self):
        return self.root_catalog_first_cluster_number * self.sectors_per_cluster

    def get_data_area_start_sector(self):
        return self.reserved_sectors + self.fat_amount * self.sectors_per_fat

    def _parse_dir_files(self, content):
        bytes_per_entry = 32

        start = 0

        files = list()
        self._long_name_buffer = ""

        while start < len(content):
            first_byte = content[start]
            if first_byte == b'\x00':
                break
            elif first_byte != b'\xE5':
                self._parse_directory_entry(content,start)

            start += bytes_per_entry

    def _parse_directory_entry(self,content, start):
        attributes = self.parse_int(start + 11, 1)
        if attributes == fs_objects.LFN:  # Long file name entry
            pass
        else:
            is_dir = attributes & fs_objects.DIRECTORY

            name = self.parse_string(start, 8, "ascii").strip()
            extension = self.parse_string(start + 8, 3, "ascii").strip()
            short_name = name + '.' + extension

            full_name = self._long_name_buffer
            if full_name:
                self._long_name_buffer = ""

            creation_time_millis = self.parse_int(start + 13, 1)
            creation_datetime = self.parse_time_date(start + 14)
            creation_datetime += timedelta(milliseconds=creation_time_millis)

            last_access_date = self.parse_date(start + 18)
            last_modification_datetime = self.parse_time_date(start + 22)

            cluster_number = (self.parse_int(start + 20, 2) << 16 + self.parse_int(start + 26, 2))
            cluster_number = cluster_number & 0b0000111111111111  # Removing unused in FAT32 address 4 highest bits

        file_size_bytes = self.parse_int(start + 28, 4)

        content = self.get_content(cluster_number)
        if is_dir:
            content = self._parse_dir_files()

    def parse_int(self, start, length):
        return int.from_bytes(self._bytes[start:start + length], byteorder='little', signed=False)

    def parse_string(self, start, length, encoding):
        return self._bytes[start: start + length].decode(encoding=encoding)

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


def slice_length(arr, start, length):
    return arr[start:start + length]
