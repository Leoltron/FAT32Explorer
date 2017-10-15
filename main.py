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

# (Файл)
# Засунуть в DirectoryBrowser файл
# Определить кол-во требуемых кластеров и их номера(из Fx INFO?)
# Сгенерировать запись для директории и дополнить её (в т.ч. выделив доп. кластер)
# Записать данные в FAT и  кластеры данных
# Обновить FSINFO (?)

# 6. Приложить тестовые образы:
#   1. Автоматически скачивать (если получится)
#   2. В readme указать ссылку, откуда скачивать
#   3. 2 образа: нормальный и с ошибками

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
