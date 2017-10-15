# !/usr/bin/env python3
import datetime

import os
import re

from pathlib import Path

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
                 create_datetime=datetime.datetime.now(),
                 last_open_date=datetime.date.today(),
                 change_datetime=datetime.datetime.now(),
                 size_bytes=0):
        self.short_name = short_name
        self.long_name = long_name
        self.attributes = attributes
        self.create_datetime = create_datetime
        self.last_open_date = last_open_date
        self.change_datetime = change_datetime
        self._size_bytes = size_bytes

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
               and self.content == other.content \
               and self.attributes == other.attributes \
               and self.create_datetime == other.create_datetime \
               and self.last_open_date == other.last_open_date \
               and self.change_datetime == other.change_datetime \
               and self._size_bytes == other._size_bytes

    def _eq_debug(self, other):
        eq_debug('\"' + self.short_name + '\"', '\"' + other.short_name + '\"')
        eq_debug('\"' + self.long_name + '\"', '\"' + other.long_name + '\"')
        eq_debug(self.content, other.content)
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
        if size < 2 ** 10:
            return bytes_str

        bytes_str = "(" + bytes_str + ")"

        if size >= 2 ** 40:
            short_str = "{:.2f} TiB ".format(size / (2 ** 40))
        elif size >= 2 ** 30:
            short_str = "{:.2f} GiB ".format(size / (2 ** 30))
        elif size >= 2 ** 20:
            short_str = "{:.2f} MiB ".format(size / (2 ** 20))
        else:
            short_str = "{:.2f} KiB ".format(size / (2 ** 10))

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
        file.content = open(external_name, "rb").read()
        file._size_bytes = len(file.content)

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
