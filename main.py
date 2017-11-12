# !/usr/bin/env python3

import sys
import fateditor
from dirbrowser import DirectoryBrowser
from pathlib import Path
import platform

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
        start = 1
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

    try:
        with open(image_file_name, "r+b") as fi:
            f = fateditor.Fat32Editor(fi, scandisk)
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
    except fateditor.FATReaderError as e:
        print("Error: " + e.message)
        return
    except PermissionError:
        error_message = "Error: permission denied."
        system = platform.system()
        if system == 'Linux':
            error_message += " You might want to run this command " \
                             "as superuser."
        elif system == 'Windows':
            error_message += " You might want to run this command " \
                             "as administrator."
        print(error_message)


def print_usage():
    print("Usage: " + sys.argv[0] + " [-s] [-l] [-i] [-z] [-h] <file_name>")


if __name__ == '__main__':
    main()
