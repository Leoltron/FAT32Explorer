# !/usr/bin/env python3

# Разбор FAT32
# Вход: образ диска с файловой системой FAT32.
#
# Реализовать утилиту для чтения файлов и просмотра листингов директорий.

import fat_reader
from directory_browser import DirectoryBrowser

def main():
    fi = open("TEST-IMAGE", "rb")
    try:
        f = fat_reader.Fat32Reader(fi.read())
    finally:
        fi.close()
    d = f.get_root_directory()
    DirectoryBrowser(d).start_interactive_mode()


if __name__ == '__main__':
    main()
