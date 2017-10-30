# !/usr/bin/env python3
import datetime

import os
import re

from pathlib import Path

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
        return ", ".join(attributes_list)

    @property
    def size_bytes(self):
        size = self._size_bytes
        if self.is_directory:
            for file in self.content:
                size += file.size_bytes
        return size

    def get_size_str(self):
        size = self.size_bytes

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

    def update_last_open_date(self):
        self.last_open_date = datetime.date.today()

    def get_dir_hierarchy(self):
        hierarchy = dict()
        if self.is_directory:
            for file in self.content:
                hierarchy[file.name] = file.get_dir_hierarchy()
        return hierarchy

    def to_directory_entry(self, start_cluster):
        pass

    def get_file_content(self, fat_reader):
        content = fat_reader.get_data_from_cluster_chain(self._start_cluster)
        if self._size_bytes >= 0:
            return content[:self._size_bytes]
        return content


def eq_debug(one, other):
    print(str(one) + (" == " if one == other else" != ") + str(other))


def get_file_from_external(external_name) -> File:
    external_path = Path(external_name)
    if not external_path.exists():
        raise FileNotFoundError('File "{}" not found.'.format(external_name))

    name = external_name.replace("\\", "/").rsplit("/", maxsplit=1)[-1]

    short_name_splitted = get_short_name(name)
    short_name = short_name_splitted[0] + (("." + short_name_splitted[1])
                                           if short_name_splitted[1] else "")

    file = File(short_name=short_name, long_name=name)

    if external_path.is_dir():
        size = 0
        file.attributes = DIRECTORY
        file.content = list()
        for name in os.listdir(str(external_path.resolve())):
            dir_file = get_file_from_external(
                external_name.replace("\\", "/") + "/" + name)
            file.content.append(dir_file)
            size += dir_file.size_bytes
        file._size_bytes = size
    else:
        file.external_name = external_name

    return file


def get_short_name(name):
    splitted_name = name.rsplit('.', maxsplit=1)
    name = splitted_name[0]
    extension = "" if len(splitted_name) == 1 else splitted_name[1]

    name = name.replace(".", "")
    name = re.sub(r"[^a-zA-Z]", "_", name)
    if len(name) > 8:
        name = name[:6] + "~1"

    extension = extension[:3]

    return name.upper(), extension.upper()


def requires_lfn(name):
    short_name_splitted = get_short_name(name)
    short_name = short_name_splitted[0] + (("." + short_name_splitted[1])
                                           if short_name_splitted[1] else "")
    return name != short_name
