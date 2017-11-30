# !/usr/bin/env python3
import platform

import fateditor
from dirbrowser import DirectoryBrowser
from pathlib import Path
import argparse

SCANDISK_ARGS = ["-l", "-i", "-z"]


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

    try:
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
