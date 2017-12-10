# !/usr/bin/env python3

import os
from datetime import datetime, date, time

DEBUG_MODE = False


def debug(message):
    if DEBUG_MODE:
        print(message)


class BytesParser:
    def __init__(self, byte_arr):
        self.byte_arr = byte_arr

    def get_bytes(self, start, length):
        return self.get_bytes_end(start, start + length)

    def get_bytes_end(self, start, end):
        return self.byte_arr[start:end]

    def parse_int_unsigned(self, start, length, byteorder='little'):
        return int.from_bytes(self.get_bytes(start, length),
                              byteorder=byteorder, signed=False)

    def parse_string(self, start, length, encoding, errors="strict"):
        return self.get_bytes(start, length).decode(encoding=encoding,
                                                    errors=errors)

    def parse_ascii_string_replace_errors(self, start, length,
                                          replacement='\u2592'):
        return ''.join(chr(byte) if byte in range(128) else replacement
                       for byte in self.get_bytes(start, length))

    def parse_time_date(self, start):
        parsed_time = self.parse_time(start)
        parsed_date = self.parse_date(start + 2)

        return datetime.combine(date=parsed_date, time=parsed_time)

    def parse_time(self, start):
        bin_string = self.parse_bin_str(start, 2)

        debug("parse_time: " + bin_string)
        debug("\th: " + bin_string[0:5])
        debug("\tm: " + bin_string[5:11])
        debug("\ts: " + bin_string[11:16])

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
        return bin(self.parse_int_unsigned(start_byte, length_bytes,
                                           byteorder="little"))[2:].zfill(
            8 * length_bytes)

    def hex_readable(self, start=0, length=None):
        if length is None:
            length = len(self)
        import binascii
        h = str(binascii.hexlify(self.get_bytes(start, length)))[
            2:-1].upper()
        return ' '.join(a + b for a, b in zip(h[::2], h[1::2]))

    def __len__(self):
        return len(self.byte_arr)


# noinspection PyMissingConstructor
class FileBytesParser(BytesParser):
    def __init__(self, file, start=0):
        if file is None:
            raise ValueError("file cannot be None!")
        self.file = file
        self._start = start

    def get_bytes(self, start, length):
        self.file.seek(self._start + start)
        return self.file.read(length)

    def get_bytes_end(self, start, end):
        length = end - start

        if length < 0:
            raise ValueError("Length must be positive!")
        elif length == 0:
            return b''

        return self.get_bytes(start, length)

    def __len__(self):
        return os.fstat(self.file).st_size


def int_to_bytes(length, value, byteorder="little"):
    return int.to_bytes(value, length=length, byteorder=byteorder)


def datetime_to_bytes(date_time):
    date_bytes = date_to_bytes(date_time.date())
    time_bytes = time_to_bytes(date_time.time())
    return time_bytes + date_bytes


def time_to_bytes(time_):
    return int(time_to_bits(time_), 2).to_bytes(length=2, byteorder="little")


def date_to_bytes(date_):
    return int(date_to_bits(date_), 2).to_bytes(length=2, byteorder="little")


def date_to_bits(date):
    year_bin = bin(date.year - 1980)[2:].zfill(7)
    month_bin = bin(date.month)[2:].zfill(4)
    day_bin = bin(date.day)[2:].zfill(5)
    result = year_bin + month_bin + day_bin
    debug("date_to_bits: " + result)
    return result


def time_to_bits(time):
    hour_bin = bin(time.hour)[2:].zfill(5)
    minute_bin = bin(time.minute)[2:].zfill(6)
    seconds_bin = bin(time.second // 2)[2:].zfill(5)
    result = hour_bin + minute_bin + seconds_bin
    debug("time_to_bits: " + result)
    return result
