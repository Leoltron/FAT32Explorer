# !/usr/bin/env python3
from main import debug

READ_ONLY = 0x01
HIDDEN = 0x02
SYSTEM = 0x04
VOLUME_ID = 0x08
DIRECTORY = 0x10
ARCHIVE = 0x20
LFN = READ_ONLY | HIDDEN | SYSTEM | VOLUME_ID


class File:
    def __init__(self,
                 short_name,
                 long_name,
                 attributes,
                 create_datetime,
                 last_open_date,
                 change_datetime,
                 size_bytes):
        self.short_name = short_name
        self.long_name = long_name
        self.attributes = attributes
        self.create_datetime = create_datetime
        self.last_open_date = last_open_date
        self.change_datetime = change_datetime
        self.size_bytes = size_bytes

    @property
    def is_directory(self):
        return bool(self.attributes & DIRECTORY)

    @property
    def name(self):
        return self.long_name if self.long_name else self.short_name

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


def eq_debug(one, other):
    debug(str(one) + (" == " if one == other else" != ") + str(other))
