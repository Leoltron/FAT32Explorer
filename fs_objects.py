# !/usr/bin/env python3

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
                 content,
                 attributes,
                 create_datetime,
                 last_open_date,
                 change_datetime,
                 size_bytes):
        self.short_name = short_name
        self.long_name = long_name
        self.content = content
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
