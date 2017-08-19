# !/usr/bin/env python3
import datetime

READ_ONLY = 0x01
HIDDEN = 0x02
SYSTEM = 0x04
VOLUME_ID = 0x08
DIRECTORY = 0x10
ARCHIVE = 0x20
LFN = READ_ONLY | HIDDEN | SYSTEM | VOLUME_ID


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
        self.size_bytes = size_bytes

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
        return (
                   self.parent.get_absolute_path() if self.parent is not None else "") + "/" + self.name

    def __eq__(self, other):
        self._eq_debug(other)
        return self.short_name == other.short_name \
               and self.long_name == other.long_name \
               and self.content == other.content \
               and self.attributes == other.attributes \
               and self.create_datetime == other.create_datetime \
               and self.last_open_date == other.last_open_date \
               and self.change_datetime == other.change_datetime \
               and self.size_bytes == other.size_bytes

    def _eq_debug(self, other):
        eq_debug('\"' + self.short_name + '\"', '\"' + other.short_name + '\"')
        eq_debug('\"' + self.long_name + '\"', '\"' + other.long_name + '\"')
        eq_debug(self.content, other.content)
        eq_debug(self.attributes, other.attributes)
        eq_debug(self.create_datetime, other.create_datetime)
        eq_debug(self.last_open_date, other.last_open_date)
        eq_debug(self.change_datetime, other.change_datetime)
        eq_debug(self.size_bytes, other.size_bytes)

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

    def get_size_str(self):
        bytes_str = "{} {}".format(self.size_bytes,
                                   "byte" if self.size_bytes == 1 else "bytes")
        if self.size_bytes < 2 ** 10:
            return bytes_str

        bytes_str = "(" + bytes_str + ")"

        if self.size_bytes >= 2 ** 40:
            short_str = "{.2f} TiB ".format(self.size_bytes / (2 ** 40))
        elif self.size_bytes >= 2 ** 30:
            short_str = "{.2f} GiB ".format(self.size_bytes / (2 ** 30))
        elif self.size_bytes >= 2 ** 20:
            short_str = "{.2f} MiB ".format(self.size_bytes / (2 ** 20))
        else:
            short_str = "{.2f} KiB ".format(self.size_bytes / (2 ** 10))

        return short_str + bytes_str

    def update_last_open_date(self):
        self.last_open_date = datetime.date.today()


def eq_debug(one, other):
    print(str(one) + (" == " if one == other else" != ") + str(other))
