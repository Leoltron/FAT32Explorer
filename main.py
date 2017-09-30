# !/usr/bin/env python3

# Разбор FAT32
# Вход: образ диска с файловой системой FAT32.
#
# Реализовать утилиту для чтения файлов и просмотра листингов директорий.

import sys
import fat_reader
from directory_browser import DirectoryBrowser
from pathlib import Path


def main():
    image_file_name = ' '.join(sys.argv[1:])

    if not image_file_name:
        print("Usage: " + sys.argv[0] + " <file_name>")
        return

    image_file_path = Path(image_file_name)

    if not image_file_path.exists():
        print('File "' + image_file_name + '" not found.')
        return
    if not image_file_path.is_file():
        print('"' + image_file_name + '" is not a file.')
        return

    fi = open(image_file_name, "rb")
    try:
        f = fat_reader.Fat32Reader(fi.read())
    finally:
        fi.close()
    print("Image successfully parsed.")
    d = f.get_root_directory()
    DirectoryBrowser(d).start_interactive_mode()


if __name__ == '__main__':
    main()
