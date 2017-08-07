# !/usr/bin/env python3

# Разбор FAT32
# Вход: образ диска с файловой системой FAT32.
#
# Реализовать утилиту для чтения файлов и просмотра листингов директорий.

import fat



def main():
    fi = open("TEST-IMAGE", "rb")
    size = 0
    try:
        bs = fi.read()
        f = fat.Fat32(bs)
        size = len(bs)
        print(str(fat.bytes_to_int_lbe(bs, 0xb, 2)))
    finally:
        fi.close()
    print("Hello, size = " + str(size))


if __name__ == '__main__':
    main()
