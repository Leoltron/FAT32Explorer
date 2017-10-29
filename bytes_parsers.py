# !/usr/bin/env python3

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

    def hex_readable(self, start, length):
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
