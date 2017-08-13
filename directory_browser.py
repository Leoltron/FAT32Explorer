# !/usr/bin/env python3

import fs_objects


def get_dir_content_names(file):
    print(file.is_directory)
    if not file.is_directory:
        raise ValueError(file.name + " is not a directory!")
    for f in file.content:
        yield f.name


class DirectoryBrowser:
    def __init__(self, root_directory):
        self.root = self.current = root_directory
        self._int_running = False

    def start_interactive_mode(self):
        self._int_running = True
        while self._int_running:
            command = input(self.current.get_absolute_path() + ">")
            self.process_command(*command.split(" ", 1))

    def print_help(self, args):
        pass

    def quit(self, args):
        self._int_running = False

    _commands = {"help": print_help, "quit": quit}

    def process_command(self, command, args_string=""):
        if command in self._commands:
            self._commands[command](args_string)
        else:
            print('Wrong command. Print "help" to get list of commands')
