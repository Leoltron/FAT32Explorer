# !/usr/bin/env python3
import datetime

import os
import re

from pathlib import Path

import itertools

import bytes_parsers

BYTES_PER_TIB = 2 ** 40
BYTES_PER_GIB = 2 ** 30
BYTES_PER_MIB = 2 ** 20
BYTES_PER_KIB = 2 ** 10

READ_ONLY = 0x01
HIDDEN = 0x02
SYSTEM = 0x04
VOLUME_ID = 0x08
DIRECTORY = 0x10
ARCHIVE = 0x20
LFN = READ_ONLY | HIDDEN | SYSTEM | VOLUME_ID

DEBUG_MODE = False


def get_size_str(size):
    bytes_str = "{} {}".format(size,
                               "byte" if size == 1 else "bytes")
    if size < BYTES_PER_KIB:
        return bytes_str
    bytes_str = "(" + bytes_str + ")"
    if size >= BYTES_PER_TIB:
        short_str = "{:.2f} TiB ".format(size / BYTES_PER_TIB)
    elif size >= BYTES_PER_GIB:
        short_str = "{:.2f} GiB ".format(size / BYTES_PER_GIB)
    elif size >= BYTES_PER_MIB:
        short_str = "{:.2f} MiB ".format(size / BYTES_PER_MIB)
    else:
        short_str = "{:.2f} KiB ".format(size / BYTES_PER_KIB)
    return short_str + bytes_str


class File:
    content = None
    parent = None

    def __init__(self,
                 short_name,
                 long_name,
                 attributes=0,
                 create_datetime=None,
                 last_open_date=None,
                 change_datetime=None,
                 size_bytes=0,
                 start_cluster=-1):
        self.short_name = short_name
        self.long_name = long_name
        self.attributes = attributes
        if create_datetime is None:
            create_datetime = datetime.datetime.now()
        self.create_datetime = create_datetime

        if last_open_date is None:
            last_open_date = datetime.date.today()
        self.last_open_date = last_open_date

        if change_datetime is None:
            change_datetime = datetime.datetime.now()
        self.change_datetime = change_datetime
        self._size_bytes = size_bytes
        self._start_cluster = start_cluster

    @property
    def is_read_only(self):
        return bool(self.attributes & READ_ONLY)

    @property
    def is_hidden(self):
        return bool(self.attributes & HIDDEN)

    @property
    def is_system(self):
        return bool(self.attributes & SYSTEM)

    @property
    def is_volume_id(self):
        return bool(self.attributes & VOLUME_ID)

    @property
    def is_directory(self):
        return bool(self.attributes & DIRECTORY)

    @property
    def is_archive(self):
        return bool(self.attributes & ARCHIVE)

    @property
    def name(self):
        return self.long_name if self.long_name else self.short_name

    def get_absolute_path(self):
        names = [self.name]
        file = self
        while file.parent is not None:
            names.append(file.parent.name)
            file = file.parent
        return "/".join(names[::-1])

    def __eq__(self, other):
        if DEBUG_MODE:
            self._eq_debug(other)
        return self.short_name == other.short_name \
               and self.long_name == other.long_name \
               and self.attributes == other.attributes \
               and self.create_datetime == other.create_datetime \
               and self.last_open_date == other.last_open_date \
               and self.change_datetime == other.change_datetime \
               and self._size_bytes == other._size_bytes

    def _eq_debug(self, other):
        eq_debug('\"' + self.short_name + '\"', '\"' + other.short_name + '\"')
        eq_debug('\"' + self.long_name + '\"', '\"' + other.long_name + '\"')
        eq_debug(self.attributes, other.attributes)
        eq_debug(self.create_datetime, other.create_datetime)
        eq_debug(self.last_open_date, other.last_open_date)
        eq_debug(self.change_datetime, other.change_datetime)
        eq_debug(self._size_bytes, other._size_bytes)

    def get_attributes_str(self):
        attributes_list = list()
        if self.is_read_only:
            attributes_list.append("read_only")
        if self.is_hidden:
            attributes_list.append("hidden")
        if self.is_system:
            attributes_list.append("system")
        if self.is_volume_id:
            attributes_list.append("volume_id")
        if self.is_directory:
            attributes_list.append("directory")
        if self.is_archive:
            attributes_list.append("archive")
        return ", ".join(attributes_list) if len(attributes_list) > 0 else \
            "no attributes"

    @property
    def size_bytes(self):
        size = self._size_bytes
        if self.is_directory:
            for file in self.content:
                size += file.size_bytes
        return size

    def get_size_str(self):
        size = self.size_bytes

        return get_size_str(size)

    def update_last_open_date(self):
        self.last_open_date = datetime.date.today()

    def get_dir_hierarchy(self):
        hierarchy = dict()
        if self.is_directory:
            for file in self.content:
                hierarchy[file.name] = file.get_dir_hierarchy()
        return hierarchy

    def get_file_content(self, fat_reader):
        content = fat_reader.get_data_from_cluster_chain(self._start_cluster)
        if self._size_bytes >= 0:
            return content[:self._size_bytes]
        return content

    def to_directory_entries(self, is_dot_self_entry=False,
                             is_dot_parent_entry=False):
        entries = list()

        if is_dot_self_entry and is_dot_parent_entry:
            raise ValueError(
                "Trying to form both self and parent 'dot' entry?")

        if is_dot_parent_entry:
            short_name = '..'
        elif is_dot_self_entry:
            short_name = '.'
        else:
            name = self.name
            short_name = self.short_name

            if requires_lfn(name, self.parent):
                entries += to_lfn_parts(name,
                                        get_short_name_checksum(short_name))

        file_info_entry = bytearray(32)
        file_info_entry[11] = self.attributes

        if is_dot_parent_entry or is_dot_self_entry:
            self._write_short_name(file_info_entry,
                                   custom_short_name=short_name,
                                   custom_short_ext='')
        else:
            self._write_short_name(file_info_entry)
        self._write_dates(file_info_entry)
        self._write_size(file_info_entry)
        self._write_start_cluster_number(file_info_entry)

        entries.append(bytes(file_info_entry))

        return entries

    def _write_dates(self, file_info_entry):
        file_info_entry[14:14 + 4] = \
            list(bytes_parsers.datetime_to_bytes(self.create_datetime))
        file_info_entry[18:18 + 2] = list(
            bytes_parsers.date_to_bytes(self.last_open_date))
        file_info_entry[22:22 + 4] = \
            list(bytes_parsers.datetime_to_bytes(self.change_datetime))

    def _write_size(self, file_info_entry):
        if not self.is_directory:
            file_info_entry[28:28 + 4] = \
                bytes_parsers.int_to_bytes(4, self.size_bytes, "little")

    def _write_short_name(self, file_info_entry, custom_short_name=None,
                          custom_short_ext=None):
        splitted_short_name = self.short_name.rsplit(".", 1)
        if custom_short_name is None:
            name_part = splitted_short_name[0][:8]
        else:
            name_part = custom_short_name[:8]

        if custom_short_ext is not None:
            extension_part = custom_short_ext[:3]
        else:
            extension_part = ("" if len(splitted_short_name) == 1 else \
                                  splitted_short_name[1][:3])

        name_part_bytes = name_part.encode(encoding="cp866", errors="strict")
        name_part_bytes += b'\x20' * (8 - len(name_part_bytes))

        extension_part = extension_part.encode(encoding="cp866",
                                               errors="strict")
        extension_part += b'\x20' * (3 - len(extension_part))

        file_info_entry[0:8] = list(name_part_bytes)
        if file_info_entry[0] == 0xE5:
            file_info_entry[0] = 0x05
        file_info_entry[8:11] = list(extension_part)

    def _write_start_cluster_number(self, file_info_entry):
        start_custer_number_bytes = int.to_bytes(self._start_cluster,
                                                 length=4, byteorder='big')
        file_info_entry[20:22] = start_custer_number_bytes[1::-1]
        file_info_entry[26:28] = start_custer_number_bytes[4:1:-1]

    def contains_file_with_short_name(self, short_name):
        if self.is_directory:
            for file in self.content:
                if file.short_name == short_name:
                    return True
            return False
        else:
            raise NotADirectoryError


def eq_debug(one, other):
    print(str(one) + (" == " if one == other else" != ") + str(other))


def get_short_name_checksum(short_name):
    return get_short_name_and_ext_checksum(*short_name.rsplit(".", maxsplit=1))


def fill_right(bytes_, width, fill_with=b'\x00'):
    if len(fill_with) != 1:
        raise ValueError(
            "Length of the fill_with must be 1 byte, got " + str(fill_with))
    if len(bytes_) >= width:
        return bytes_
    return bytes_ + (fill_with * (width - len(bytes_)))


def get_short_name_and_ext_checksum(name, extension=""):
    checksum = 0
    s = name.encode(encoding='cp866') + \
        (b"\x20" * (8 - len(name))) + \
        extension.encode(encoding='cp866') + \
        (b"\x20" * (3 - len(extension)))
    for char_code in s:
        carry = checksum & 1
        checksum = checksum >> 1
        if carry:
            checksum += 0b10000000
        checksum += char_code
        checksum = checksum & 0xff
    return checksum


def get_short_name(name: str, directory: File = None):
    splitted_name = name.rsplit('.', maxsplit=1)
    name = splitted_name[0]
    extension = "" if len(splitted_name) == 1 else splitted_name[1]

    name = name.replace(".", "")
    name = re.sub(r"[^0-9a-zA-Zа-яА-ЯёЁ!#$%&'()\-@^_`{}~]", "_", name).upper()
    extension = extension[:3].upper()

    if len(name) > 8 or (directory is not None and directory
            .contains_file_with_short_name(name + '.' + extension)):
        i = 1
        name = name[:6] + "~1"
        while directory is not None and \
                directory.contains_file_with_short_name(
                                    name + '.' + extension) and i < 9:
            i += 1
            name = name[:7] + str(i)

    return name + ('.' + extension if extension else "")


def to_lfn_parts(name, checksum=0):
    name_bytes = name.encode("utf-16")[2:]
    parts = list()
    i = 0
    part_number = 1
    while i < len(name_bytes):
        part = bytearray(32)
        for pos in get_utf16_char_pos():
            if i < len(name_bytes):
                part[pos] = name_bytes[i]
                part[pos + 1] = name_bytes[i + 1]
                i += 2
            elif i == len(name_bytes):
                part[pos:pos + 1] = b'\x00\x00'
                i += 2
            else:
                part[pos:pos + 1] = b'\xff\xff'
                i += 2

        part[0] = part_number if i < len(name_bytes) else 0x40 + part_number
        part[0x0b] = LFN
        part[0x0d] = checksum
        parts.append(bytes(part))
        part_number += 1
    return parts[::-1]


def get_utf16_char_pos():
    return itertools.chain(range(1, 11, 2), range(14, 26, 2),
                           range(28, 32, 2))


def requires_lfn(name, directory=None):
    short_name = get_short_name(name, directory)
    return name != short_name
