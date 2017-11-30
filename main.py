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

import fateditor
from dirbrowser import DirectoryBrowser
from pathlib import Path
import argparse


def main():
    parsed_args = parse_args()

    find_lost_clusters = parsed_args.lost_clusters
    find_intersecting_chains = parsed_args.intersections
    check_files_size = parsed_args.size
    scandisk = parsed_args.scandisk or \
               find_lost_clusters or \
               find_intersecting_chains or \
               check_files_size

    image_file_name = parsed_args.image_path
    image_file_path = Path(image_file_name)

    if not image_file_path.exists():
        print('File "' + image_file_name + '" not found.')
        return

    with open(image_file_name, "r+b") as fi:
        f = fateditor.Fat32Editor(fi, scandisk)
        if f.valid:
            print("Image successfully parsed.")
        if scandisk:
            f.scandisk(
                find_lost_clusters,
                find_intersecting_chains,
                check_files_size
            )
        else:
            DirectoryBrowser(fat_editor=f).start_interactive_mode()


def parse_args():
    parser = argparse.ArgumentParser(description="Open FAT32 image")

    parser.add_argument("image_path", type=str,
                        help="Path to the FAT32 image")

    parser.add_argument("-s", "--scandisk",
                        action="store_true",
                        help="Basic validation scan")
    parser.add_argument("-i", "--intersections",
                        action="store_true",
                        help="Scan, find and repair file chain intersections")
    parser.add_argument("-l", "--lost-clusters",
                        action="store_true",
                        help="Scan, find and free lost clusters")
    parser.add_argument("-z", "--size",
                        action="store_true",
                        help="Scan, find and repair incorrect files' size")
    return parser.parse_args()


if __name__ == '__main__':
    main()
