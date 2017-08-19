# !/usr/bin/env python3

import fs_objects


def reg_command(dict_registry, name):
    def reg(f):
        dict_registry[name] = f
        return f
    return reg


def _get_dir_content_names(file):
    print(file.is_directory)
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


def _check_for_invalid_symbols(name):
    for char in name:
        if not _is_valid_char_for_file_name(char):
            raise ValueError(char + " is prohibited in file name")


_PROHIBITED_NAME_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']


def _is_valid_char_for_file_name(char):
    return ord(char) > 31 and char not in _PROHIBITED_NAME_CHARS


class DirectoryBrowser:
    def __init__(self, root_directory):
        self.root = self.current = root_directory
        self._int_running = False

    def start_interactive_mode(self):
        self._int_running = True
        while self._int_running:
            command = input(self.current.get_absolute_path() + ">")
            try:
                self._process_command(*command.split(" ", 1))
            except DirectoryBrowserError as e:
                print(e.message)

    _commands = dict()

    def _process_command(self, command, args_string=""):
        if command in self._commands:
            self._commands[command](args_string)
        else:
            print('Wrong command. Print "help" to get list of available commands.')

    @reg_command(_commands, "help")
    def print_help(self, args):
        pass

    # noinspection PyUnusedLocal
    @reg_command(_commands, "quit")
    def stop_interactive_mode(self, args):
        self._int_running = False

    @reg_command(_commands, "cd")
    def change_directory(self, args):
        dirs = args.split("/")
        if len(dirs) > 1:
            prev_dir = self.current
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

    def find(self, name, priority=None) -> fs_objects.File:
        file_found = None
        for file in self.current.content:
            if file.name == name:
                if priority is None or (
                                priority == "directory" and file.is_directory) or (
                                priority == "file" and not file.is_directory):
                    return file
                else:
                    file_found = file
        return file_found

    @reg_command(_commands, "dir")
    def dir(self, args):
        print(self.current.get_absolute_path() + " content:")
        for file in self.current.content:
            print(file.change_datetime.strftime("%d.%m.%Y %H:%M:%S") + "    " + (
                "directory    " if file.is_directory else "   file      ") + file.name)

    @reg_command(_commands, "info")
    def info(self, args):
        pass

    @reg_command(_commands, "open")
    def open(self, args):
        pass


class DirectoryBrowserError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message
