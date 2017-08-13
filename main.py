# !/usr/bin/env python3

# Разбор FAT32
# Вход: образ диска с файловой системой FAT32.
#
# Реализовать утилиту для чтения файлов и просмотра листингов директорий.

import fat_reader

def main():
    fi = open("TEST-IMAGE", "rb")
    size = 0
    try:
        bs = fi.read()
        f = fat_reader.Fat32Reader(bs)
        d = f.get_root_directory()
        size = len(bs)
    finally:
        fi.close()
    print("Hello, size = " + str(size))


if __name__ == '__main__':
    main()
