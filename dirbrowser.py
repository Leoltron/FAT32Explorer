# !/usr/bin/env python3
import os
import platform
import re
import shutil
import subprocess

import fsobjects
from bytes_parsers import BytesParser

HEX_COMMAND_USAGE = 'hex <file> <line length>'
CP_TO_EXT_USAGE = "copyToExternal <image path> <external path>"
TYPE_USAGE = 'type <encoding> <file>'

DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"


def dispose_temp_files():
    if os.path.isdir("temp"):
        shutil.rmtree("temp")


def reg_command(dict_registry, name, usage=None, desc="", keys=list()):
    if usage is None:
        usage = name

    def reg(f):
        dict_registry[name.lower()] = (f, usage, desc, keys)
        return f

    return reg


def _get_dir_content_names(file):
    if not file.is_directory:
        raise NotADirectoryError(file.name + " is not a directory!")
    for f in file.content:
        yield f.name


def _parse_command_args_file_name(args):
    name = args.strip()
    if name[0] == '"':
        name = name[1:]
    if name[-1] == '"':
        name = name[:-1]
    _check_for_invalid_symbols(name)
    return name


def clear_from_screening_quotes(s):
    if len(s) > 0 and s[0] == '"':
        return clear_from_screening_quotes(s[1:])

    if len(s) > 0 and s[-1] == '"':
        return clear_from_screening_quotes(s[:-1])

    return s


def _check_for_invalid_symbols(name):
    for char in name:
        if not _is_valid_char_for_file_name(char):
            raise ValueError(char + " is prohibited in file name")


_PROHIBITED_NAME_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']


def _is_valid_char_for_file_name(char):
    return ord(char) > 31 and char not in _PROHIBITED_NAME_CHARS


def print_dir_content(directory, names_only, recursive):
    for file in directory.content:
        if names_only:
            print(file.name)
        else:
            print(
                file.change_datetime.strftime(DATETIME_FORMAT) + "    " +
                ("directory    " if file.is_directory else "   file      ")
                + file.name)
        if file.is_directory and recursive:
            print_dir_content(file, names_only, recursive)


def print_dir_help():
    print(
        "dir - prints the content of current directory\n"
        "   /b - print only file names\n"
        "   /s - print files of directory and all"
        " its subdirectories.\n")


def save_file_at_external(file, path, fat_reader):
    path = path.replace("\\", "/")

    splitted_path = path.rsplit("/", maxsplit=1)
    directory = splitted_path[0] if len(splitted_path) > 1 else ""
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    if file.is_directory:
        for dir_file in file.content:
            save_file_at_external(dir_file, path + "/" + dir_file.name,
                                  fat_reader)
    else:
        file_content = file.get_file_content(fat_reader)
        try:
            with open(path, "wb") as system_file:
                if file_content:
                    system_file.write(file_content)
        except PermissionError:
            raise DirectoryBrowserError("Error: permission denied.")


def find(name, source, priority=None) -> fsobjects.File:
    if len(name) > 2 and name[0] == '"' and name[-1] == '"':
        name = name[1:-1]
    dirs = name.split("/", maxsplit=1)
    if len(dirs) > 1:
        return find(dirs[1], source=find(dirs[0], source=source,
                                         priority="directory"),
                    priority=priority)
    if name == ".":
        return source
    elif name == "..":
        return source.parent
    file_found = None
    for file in source.content:
        if file.name == name:
            if priority is None or (
                            priority == "directory" and file.is_directory
            ) or (
                            priority == "file" and not file.is_directory):
                return file
            else:
                file_found = file
    return file_found


screened_file_path_regex = re.compile(r"\s*\"([^<>\"|?*]+)\"")
file_path_regex = re.compile(r"\s*([^<>\"|?*\s]+)")


def parse_file_args(args, amount=1):
    parsed_args = []
    while amount > 0:
        match = screened_file_path_regex.match(args)
        if match is None:
            match = file_path_regex.match(args)
            if match is None:
                raise DirectoryBrowserError(
                    "Expected {:d} arguments, got {:d}".format(
                        amount + len(parsed_args), len(parsed_args)))
        parsed_args.append(match.group(1))
        match_length = len(match.group(0))
        args = "" if match_length >= len(args) else args[match_length:]
        amount -= 1
    return parsed_args


class DirectoryBrowser:
    def __init__(self, fat_editor=None, root=None):
        self.root = self.current = fat_editor.get_root_directory() \
            if root is None else root
        self._fat_editor = fat_editor
        self._int_running = False

    def start_interactive_mode(self):
        self._int_running = True
        while self._int_running:
            command = input(self.current.get_absolute_path() + ">")
            try:
                self._process_command(*command.split(" ", 1))
            except DirectoryBrowserError as e:
                print(e.message)
            except Exception:
                dispose_temp_files()
                raise
        dispose_temp_files()

    _commands = dict()

    def _process_command(self, command, args_string=""):
        if command.lower() in self._commands:
            self._commands[command.lower()][0](self, args_string)
        else:
            print('Wrong command. '
                  'Print "help" to get list of available commands.')

    # noinspection PyUnusedLocal
    @reg_command(_commands, "help", usage="help", desc="prints help")
    def print_help(self, args):
        command_names = list(self._commands.keys())
        command_names.sort()
        usage_max_len = max(len(c[1]) for c in self._commands.values())
        for command_name in command_names:
            value = self._commands[command_name]
            usage = value[1]
            desc = value[2]
            print(usage.ljust(usage_max_len) + ' - ' + desc)

            keys = value[3]
            if len(keys) > 0:
                max_key_len = max(len(k[0]) for k in keys)
                for key, key_desc in keys:
                    print('\t ' + key.ljust(max_key_len) + ' - ' + key_desc)
                print()

    # noinspection PyUnusedLocal
    @reg_command(_commands, "quit", desc="quits the interactive mode")
    def stop_interactive_mode(self, args):
        self._int_running = False

    @reg_command(_commands, "cd", usage="cd <directory>",
                 desc="changes directory")
    def change_directory(self, args):
        if len(args) == 0:
            raise DirectoryBrowserError("Usage: cd <folder name>")

        if '\\' in args:
            dirs = args.split("\\")
        else:
            dirs = args.split("/")

        if len(dirs) > 1:
            prev_dir = self.current
            if args[0] == '/':
                self.current = self.root
                if args == '/':
                    return
                dirs = dirs[1:]
            try:
                for directory in dirs:
                    self.change_directory(directory)
            except Exception:
                self.current = prev_dir
                raise
        else:
            name = _parse_command_args_file_name(args)
            path = self.current.get_absolute_path() + "/" + name
            file = self.find(name, priority="directory")
            if file is None:
                raise DirectoryBrowserError(path + " not found.")
            elif not file.is_directory:
                raise DirectoryBrowserError(path + " is not a directory.")
            else:
                self.current = file

    def _get_parent_dir(self):
        if self.current.parent is not None:
            return self.current.parent
        else:
            raise DirectoryBrowserError(
                ("Root" if self.current == self.root else "Current") +
                " directory does not have a parent directory!")

    @reg_command(_commands, "dir", usage='dir [/b] [/s]',
                 desc="prints the content of current directory",
                 keys=[("/b", "print only file names"),
                       ("/s",
                        "print files of directory and all its subdirectories")]
                 )
    def dir(self, args):
        flags = args.split(" ")
        if '/?' in flags:
            print_dir_help()
            return
        recursive = '/s' in flags or '-s' in flags
        names_only = '/b' in flags or '-b' in flags
        print('"' + self.current.get_absolute_path() + '" content:')
        print_dir_content(self.current, names_only, recursive)

    @reg_command(_commands, "info", usage="info <file>",
                 desc="prints info about the file")
    def info(self, args):
        file = self.find(args)
        if file is None:
            raise DirectoryBrowserError(args + " not found.")
        print("info about file " + file.get_absolute_path() + ":")
        print("\tShort name: " + file.short_name)
        if file.long_name:
            print("\tLong name: " + file.long_name)
        print("\tAttributes: " + file.get_attributes_str())
        print("\tCreation date/time: " + file.create_datetime.strftime(
            DATETIME_FORMAT))
        print("\tLast change date/time: " + file.change_datetime.strftime(
            DATETIME_FORMAT))
        print("\tLast opened: " + file.last_open_date.strftime("%d.%m.%Y"))
        print("\tSize: " + file.get_size_str())

    @reg_command(_commands, "copyToExternal",
                 usage=CP_TO_EXT_USAGE,
                 desc="copy file to external storage")
    def copy_to_external(self, args):
        if "/?" in args:
            raise DirectoryBrowserError("Usage: " + CP_TO_EXT_USAGE)
        try:
            image_file_path, external_file_path = parse_file_args(args, 2)
        except DirectoryBrowserError:
            raise DirectoryBrowserError("Usage: " + CP_TO_EXT_USAGE)

        file = self.find(image_file_path)
        if file is None:
            raise DirectoryBrowserError(image_file_path + " not found.")
        save_file_at_external(file, external_file_path, self._fat_editor)

    @reg_command(_commands, "open", usage='open <file>',
                 desc="cd, if file is a directory, otherwise make a temporary"
                      " copy of the file and try to open it trough system")
    def open(self, args):
        file = self.find(args)
        if file is None:
            raise DirectoryBrowserError(args + " not found.")

        if file.is_directory:
            self.current = file
        else:
            path = "temp" + file.get_absolute_path()
            save_file_at_external(file, path, self._fat_editor)

            system = platform.system()
            if system == 'Linux':
                subprocess.call(["xdg-open", path])
            elif system == 'Windows':
                os.startfile(path.replace("/", "\\"))
        file.update_last_open_date()

    @reg_command(_commands, "type", usage=TYPE_USAGE,
                 desc='prints file content as if it were text file')
    def type(self, args):
        args_splitted = args.split(" ", maxsplit=1)
        if len(args_splitted) != 2:
            raise DirectoryBrowserError('Usage: %s' % TYPE_USAGE)
        encoding = args_splitted[0]
        file_name = args_splitted[1]
        file = self.find(file_name, priority="file")
        if file is None:
            raise DirectoryBrowserError('File "' + file_name + '" not found.')
        if file.is_directory:
            raise DirectoryBrowserError('"' + file_name + '" is a directory.')
        bytes_parser = BytesParser(file.get_file_content(self._fat_editor))
        text = bytes_parser.parse_string(0, len(bytes_parser),
                                         encoding=encoding)
        print(text)

    @reg_command(_commands, "hex",
                 usage=HEX_COMMAND_USAGE,
                 desc='prints file content as bytes in hex form')
    def hex(self, args):
        args_splitted = args.rsplit(" ", maxsplit=1)
        if len(args_splitted) != 2:
            raise DirectoryBrowserError('Usage: ' + HEX_COMMAND_USAGE)
        file_name = args_splitted[0]
        line_len_str = args_splitted[1]

        try:
            line_len = int(line_len_str)
        except ValueError as e:
            raise DirectoryBrowserError("Line length format error: " + str(e))
        if line_len <= 0:
            raise DirectoryBrowserError("Line length must be positive!")

        file = self.find(file_name, priority="file")
        if file is None:
            raise DirectoryBrowserError('File "' + args + '" not found.')
        if file.is_directory:
            raise DirectoryBrowserError('"' + args + '" is a directory.')
        byte_content = file.get_file_content(self._fat_editor)
        for start in range(0, len(byte_content), line_len):
            line = ""
            for part in range(start, min(start + line_len, len(byte_content))):
                if not len(line) == 0:
                    line += " "
                line += format(byte_content[part], '02x')
            print(line)

    @reg_command(_commands, "copyToImage",
                 usage="copyToImage <external path> <image path>",
                 desc="copy file from external path to image")
    def copy_to_image(self, args):
        external_path, image_path = parse_file_args(args, 2)

        try:
            current = self.current.get_absolute_path() if self.current != self.root else "."
            self._fat_editor.write_to_image(external_path, image_path)
            self.root = self.current = self._fat_editor.get_root_directory()
            self.change_directory(current)
        except Exception as e:
            raise DirectoryBrowserError(str(e))

    def find(self, name, source=None, priority=None) -> fsobjects.File:
        if source is None:
            source = self.current
        return find(name=name, source=source, priority=priority)


class DirectoryBrowserError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message
