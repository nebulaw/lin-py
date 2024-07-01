#!/bin/env python

import re
import os
import argparse
from argparse import ArgumentParser
from tabulate import tabulate
from typing import List
from functools import partialmethod

"""
The only problem in this code is that it pretty much is
designed to work only in runtime. Might redesign later
"""


__version__ = "0.001"
__author__ = "Karlo Tsutskiridze"

"""
These are base classes and its easy to add new commands.
you can use `LinStatus` class as an example to add a new command atm
"""

class _LinCommand:
    COMMAND: str = ""
    """Base class for all commands"""
    @staticmethod
    def attach_subparser(subparsers) -> ArgumentParser: raise NotImplementedError
    def process(self) -> None: raise NotImplementedError

class _LinCore:
    """Core class and acts like a kernel for the tool"""
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog="lin",
            description="A simple tool to overview your projects",
            epilog="lin"
        )
        self.parser._optionals.title = "Options"
        self.parser.add_argument("-v", "--verbose", action="store_true")
        self.subparsers = self.parser.add_subparsers(title="Subcommands", required=True, dest="subcommand")
        self.args = []

    def get_version(self): return f"lin version {__version__}"

    def get_author(self): return f"Author: {__author__}"

    def get_project_base_path(self) -> str | None:
        # check if current directory contains .lininfo file
        # if it does, return the current directory else search
        # .lininfo file in parent directories

        # save cwd
        saved_cwd = os.getcwd()
        temp_cwd = saved_cwd
        home_dir = os.getenv("HOME")

        # this checks for .lininfo file in parent directories
        while True:
            # TODO: check if file is a directory and return corresponding result
            if ".lininfo" in os.listdir(temp_cwd):
                return temp_cwd if os.path.isfile(os.path.join(temp_cwd, ".lininfo")) else None
            if temp_cwd == home_dir: break
            os.chdir("..")
            temp_cwd = os.getcwd()
        # return to saved cwd
        os.chdir(saved_cwd)
        return None

    def parse(self): self.args = self.parser.parse_args()

    def register_command(self, cls: _LinCommand):
        if self.subparsers: cls.attach_subparser(self.subparsers)
        setattr(_LinCore, cls.COMMAND, cls.process)
        # setattr(_LinCore, cls.COMMAND + "_attach_parser", cls.attach_subparser)
        # getattr(_LinCore, cls.COMMAND + "_attach_parser")()

    def execute(self):
        getattr(_lincore, _lincore.args.subcommand)()
_lincore = _LinCore()


class LinStatus(_LinCommand):
    COMMAND = "status"

    @staticmethod
    def attach_subparser(subparsers) -> ArgumentParser:
        st_parser = subparsers.add_parser(LinStatus.COMMAND, help="Generate statistics")
        st_parser.add_argument("path", nargs="*", default=".", help="Path or paths to show statistics for")
        st_parser.add_argument("-s", "--sort", default="L", type=str, choices="ALW", )
        st_parser.add_argument("-r", "--relpath", action="store_true")
        return st_parser

    def process(self) -> None:
        if not self.args: raise ValueError("Arguments are not parsed")
        headers = ["Name", "Lines", "Max Width", "Avg Width"]
        print(tabulate(construct_table(self.args.path, sort=self.args.sort, show_relpath=self.args.relpath), headers=headers))
_lincore.register_command(LinStatus)


class LinIgnore(_LinCommand):
    COMMAND = "ignore"

    @staticmethod
    def attach_subparser(subparsers) -> ArgumentParser:
        ig_parser = subparsers.add_parser(LinIgnore.COMMAND, help="Command to add, modify or delete ignoring paths")
        ig_parser.add_argument("path", nargs="+", help="Specify path or paths")
        ig_parser.add_argument("-l", "--list", action="store_true")
        ig_parser.add_argument("-r", "--remove", action="store_true")
        ig_parser.add_argument("-t", "--title", default=None)
        return ig_parser

    def process(self) -> None:
        if not self.args: raise ValueError("Arguments are not parsed")
        project_base_path = _lincore.get_project_base_path()
        if not project_base_path:
            return
        ignore_path = os.path.join(project_base_path, ".linignore")

        def read_ignored_paths(path) -> List[str]:
            try:
                ignore_file = open(path, "r")
                return ignore_file.read().splitlines()
            except FileNotFoundError: print("File not found"); return []

        def extract_ignored_content(lines):
            ffxn = lambda line: line != "" and not line.isspace() and not line.startswith("#")
            return list(filter(ffxn, lines))

        def write_ignore_file(path, lines):
            ignore_file = open(path, "w")
            ignore_file.writelines([line + "\n" for line in lines])

        ignore_file_lines = read_ignored_paths(ignore_path)
        ignore_file_content = extract_ignored_content(ignore_file_lines)
        paths_to_ignore = self.args.path

        # title for the content if its provided
        paths_to_ignore = [path for path in paths_to_ignore if path not in ignore_file_content]

        if paths_to_ignore == []: return

        if self.args.title:
            ignore_file_lines.append("\n# " + self.args.title)

        for path_to_ignore in paths_to_ignore:
            if path_to_ignore not in ignore_file_content:
                ignore_file_lines.append(path_to_ignore)

        write_ignore_file(ignore_path, ignore_file_lines)

        print(f"base path: {project_base_path}")
        print(f"ignored: {ignore_file_content}")
        print(f"to ignore: {paths_to_ignore}")

_lincore.register_command(LinIgnore)


def generate_path_stats(base_path=".", sort="L", reverse=False, show_relpath=False):
    def get_stat(path):
        with open(path, "r") as file:
            path = os.path.relpath(path, base_path) if show_relpath else path
            try: lines = file.readlines()
            except: return []
            line_count = len(lines)
            if line_count == 0: return []
            line_widths = [len(line) for line in lines]
            max_line_width = max(line_widths)
            avg_line_width = round(sum(line_widths) / line_count, 2)
            return [path, line_count, max_line_width, avg_line_width]

    table = []
    for path, _, files in os.walk(base_path):
        for filename in files:
            # TODO: ignore specific files
            # if not filename.endswith(""): continue

            # TODO: ignore specific paths
            filepath = os.path.join(path, filename)

            # TODO: generate stats in a better way
            table.append(get_stat(filepath))

    # sort table and return
    sort_ix = "ALW".index(sort)
    sort_key = lambda x: x[sort_ix] if sort_ix == 0 else -x[sort_ix]
    return sorted(filter(lambda x: x != [], table), key=sort_key)

def construct_table(base_paths=["."], **kwargs) -> List[List[any]]:
    table = []
    for base_path in base_paths:
        table.extend(generate_path_stats(base_path=base_path, **kwargs))
    return table

if __name__ == "__main__":
    # parse arguments
    _lincore.parse()
    # execute command
    _lincore.execute()

