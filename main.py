# !/usr/bin/env python3

# Разбор FAT32
# Вход: образ диска с файловой системой FAT32.
#
# Реализовать утилиту для чтения файлов и просмотра листингов директорий.

# 1. Доп.утилита "scandisk":
#   1.1 Быстрая проверка, что образ действительно FAT32
#       (Готово, проверка по составу сектора FSInfo)
#   1.2 Если несколько таблиц, проверить что они совпадают (Готово)
#   1.3 С доп.опциями проверять наличие потерянных файлов, пересекающихся
#       цепочек и неверных размеров файлов
#   1.4 Сделать исправление ошибок ^^^
# 2. Возможность просмотра файлов (text, hex) (Готово)
# 3. dir /b, /s (Готово)
# 4. Возможность копирования файлов и каталогов на хостовую машину
#    (с указанием места назначения) (Готово)
# 5. Возможность копирования файлов и каталогов с хостовой машины в образ

# 6. Приложить тестовые образы:
#   1. Автоматически скачивать (если получится) (Готово)
#   2. В readme указать ссылку, откуда скачивать (Не требуется)
#   3. 2 образа: нормальный и с ошибками

import sys
import fat_editor
from directory_browser import DirectoryBrowser
from pathlib import Path

SCANDISK_ARGS = ["-l", "-i", "-z"]


def main():
    if len(sys.argv) == 1 or '-h' in sys.argv:
        print_usage()
        return

    scandisk = False
    find_lost_sectors = False
    find_intersecting_chains = False
    check_files_size = False
    if sys.argv[1] in ['-s'] + SCANDISK_ARGS:
        scandisk = True
        start = 2
        while start < len(sys.argv):
            if sys.argv[start] == '-l':
                find_lost_sectors = True
            elif sys.argv[start] == '-i':
                find_intersecting_chains = True
            elif sys.argv[start] == '-z':
                check_files_size = True
            elif sys.argv[start] != '-s':
                break
            start += 1

        image_file_name = ' '.join(sys.argv[start:])
    else:
        image_file_name = ' '.join(sys.argv[1:])

    if not image_file_name:
        print_usage()
        return

    image_file_path = Path(image_file_name)

    if not image_file_path.exists():
        print('File "' + image_file_name + '" not found.')
        return

    with open(image_file_name, "r+b") as fi:
        f = fat_editor.Fat32Editor(fi)
        if f.valid:
            print("Image successfully parsed.")
        if scandisk:
            f.scandisk(
                find_lost_sectors,
                find_intersecting_chains,
                check_files_size
            )
        else:
            DirectoryBrowser(fat_editor=f).start_interactive_mode()


def print_usage():
    print("Usage: " + sys.argv[0] + " [-s] [-l] [-i] [-z] [-h] <file_name>")


if __name__ == '__main__':
    main()
