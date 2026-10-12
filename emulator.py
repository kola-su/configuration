import argparse
import base64
import json
import os
import shlex
import socket
from datetime import datetime, timezone
import tkinter as tk
from tkinter import scrolledtext


class Node:
    """Один файл или каталог виртуальной файловой системы."""

    def __init__(self, name, kind):
        self.name = name
        self.kind = kind
        self.content = b""
        self.children = {}
        self.parent = None

    def is_dir(self):
        return self.kind == "directory"


class Shell:
    """Команды эмулятора. Дерево файлов хранится только в памяти."""

    def __init__(self, root=None):
        self.username = os.environ.get("USERNAME", os.environ.get("USER", "user"))
        self.hostname = socket.gethostname()
        self.running = True
        self.root = root or Node("", "directory")
        self.cwd = self.root
        self.previous = None

    def prompt(self):
        return f"{self.username}@{self.hostname}:{self.abs_path(self.cwd)}$ "

    def expand(self, line):
        """Подставляет $ИМЯ и ${ИМЯ}. В одинарных кавычках не подставляет."""
        result = []
        i = 0
        quote = None
        while i < len(line):
            ch = line[i]
            if quote is None and ch in ("'", '"'):
                quote = ch
                result.append(ch)
                i += 1
                continue
            if quote == ch:
                quote = None
                result.append(ch)
                i += 1
                continue
            if quote != "'" and ch == "$":
                i, value = self.read_var(line, i + 1)
                result.append(value.replace("\\", "\\\\"))
                continue
            result.append(ch)
            i += 1
        return "".join(result)

    def read_var(self, line, i):
        name = ""
        if i < len(line) and line[i] == "{":
            i += 1
            while i < len(line) and line[i] != "}":
                name += line[i]
                i += 1
            if i < len(line) and line[i] == "}":
                i += 1
        else:
            while i < len(line) and (line[i].isalnum() or line[i] == "_"):
                name += line[i]
                i += 1
        value = os.environ.get(name, "")
        if name == "HOME" and not value:
            value = os.environ.get("USERPROFILE", "")
        return i, value

    def parse(self, line):
        return shlex.split(self.expand(line), posix=True)

    def execute(self, line):
        line = line.strip()
        if not line:
            return ""
        try:
            args = self.parse(line)
        except ValueError:
            return "Ошибка разбора команды: незакрытые кавычки"
        if not args:
            return ""
        command = args[0]
        rest = args[1:]
        if command == "ls":
            return self.cmd_ls(rest)
        if command == "cd":
            return self.cmd_cd(rest)
        if command == "tree":
            return self.cmd_tree(rest)
        if command == "date":
            return self.cmd_date(rest)
        if command == "exit":
            return self.cmd_exit(rest)
        return f"Ошибка: неизвестная команда '{command}'"

    def abs_path(self, node):
        if node.parent is None:
            return "/"
        names = []
        current = node
        while current.parent is not None:
            names.append(current.name)
            current = current.parent
        return "/" + "/".join(reversed(names))

    def resolve(self, path):
        node = self.root if path.startswith("/") else self.cwd
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if node.parent is not None:
                    node = node.parent
                continue
            if not node.is_dir() or part not in node.children:
                return None
            node = node.children[part]
        return node

    def split_parent(self, path):
        trimmed = path.rstrip("/")
        if trimmed == "":
            return "/", ""
        if "/" not in trimmed:
            return "", trimmed
        parent, name = trimmed.rsplit("/", 1)
        if parent == "":
            parent = "/"
        return parent, name

    def parent_node(self, parent_path):
        if parent_path == "":
            return self.cwd
        return self.resolve(parent_path)

    def cmd_ls(self, args):
        show_all = False
        long = False
        paths = []
        for arg in args:
            if arg.startswith("-") and arg != "-":
                flags = arg[1:]
                if any(ch not in "al" for ch in flags):
                    return f"ls: неверный флаг: {arg}"
                show_all = show_all or ("a" in flags)
                long = long or ("l" in flags)
            else:
                paths.append(arg)
        if not paths:
            paths = [self.abs_path(self.cwd)]
        blocks = []
        for path in paths:
            if len(paths) > 1:
                blocks.append(path + ":")
            blocks.append(self.ls_one(path, show_all, long))
        return "\n".join(part for part in blocks if part)

    def ls_one(self, path, show_all, long):
        node = self.resolve(path)
        if node is None:
            return f"ls: нет такого файла или каталога: {path}"
        if not node.is_dir():
            return self.format_entry(node.name, node, long)
        rows = []
        if show_all:
            parent = node.parent or node
            rows.append((".", node))
            rows.append(("..", parent))
        for name in sorted(node.children):
            if show_all or not name.startswith("."):
                rows.append((name, node.children[name]))
        if long:
            return "\n".join(self.format_entry(name, item, True) for name, item in rows)
        return "  ".join(name for name, _item in rows)

    def format_entry(self, name, node, long):
        if not long:
            return name
        kind = "d" if node.is_dir() else "-"
        size = len(node.children) if node.is_dir() else len(node.content)
        return f"{kind} {size:8d} {name}"

    def cmd_cd(self, args):
        if len(args) > 1:
            return "cd: слишком много аргументов"
        if not args:
            self.previous = self.cwd
            self.cwd = self.root
            return ""
        if args[0] == "-":
            if self.previous is None:
                return "cd: нет предыдущего каталога"
            self.cwd, self.previous = self.previous, self.cwd
            return self.abs_path(self.cwd)
        node = self.resolve(args[0])
        if node is None:
            return f"cd: нет такого файла или каталога: {args[0]}"
        if not node.is_dir():
            return f"cd: не каталог: {args[0]}"
        self.previous = self.cwd
        self.cwd = node
        return ""

    def cmd_tree(self, args):
        show_all, depth, paths, error = self.parse_tree(args)
        if error:
            return error
        if len(paths) > 1:
            return "tree: слишком много аргументов"
        path = paths[0] if paths else self.abs_path(self.cwd)
        node = self.resolve(path)
        if node is None:
            return f"tree: нет такого файла или каталога: {path}"
        lines = [self.abs_path(node)]
        if node.is_dir():
            self.add_tree(lines, node, "", 1, depth, show_all)
        return "\n".join(lines)

    def parse_tree(self, args):
        show_all = False
        depth = 32
        paths = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-a":
                show_all = True
            elif arg == "-L":
                i += 1
                if i >= len(args) or not args[i].isdigit():
                    return False, 0, [], "tree: после -L нужно число"
                depth = int(args[i])
            elif arg.startswith("-L") and arg[2:].isdigit():
                depth = int(arg[2:])
            elif arg.startswith("-"):
                return False, 0, [], f"tree: неверный флаг: {arg}"
            else:
                paths.append(arg)
            i += 1
        return show_all, depth, paths, ""

    def add_tree(self, lines, node, prefix, level, limit, show_all):
        if level > limit:
            return
        names = sorted(node.children)
        if not show_all:
            names = [name for name in names if not name.startswith(".")]
        for index, name in enumerate(names):
            last = index == len(names) - 1
            branch = "└── " if last else "├── "
            lines.append(prefix + branch + name)
            child = node.children[name]
            if child.is_dir() and level < limit:
                extra = "    " if last else "│   "
                self.add_tree(lines, child, prefix + extra, level + 1, limit, show_all)

    def cmd_date(self, args):
        utc = False
        fmt = "%Y-%m-%d %H:%M:%S"
        for arg in args:
            if arg == "-u":
                utc = True
            elif arg.startswith("+"):
                fmt = arg[1:]
            else:
                return f"date: неверный аргумент: {arg}"
        now = datetime.now(timezone.utc) if utc else datetime.now()
        try:
            return now.strftime(fmt)
        except ValueError as error:
            return f"date: {error}"

    def cmd_exit(self, args):
        if args:
            return "Ошибка: exit не принимает аргументы"
        self.running = False
        return "Выход из эмулятора."


def build_node(name, data, parent):
    kind = data.get("type")
    node = Node(name, kind)
    node.parent = parent
    if kind == "file":
        raw = data.get("content", "")
        if data.get("encoding") == "base64":
            node.content = base64.b64decode(raw)
        else:
            node.content = str(raw).encode("utf-8")
        return node
    for child in data.get("children", []):
        item = build_node(child["name"], child, node)
        node.children[item.name] = item
    return node


def load_vfs(path):
    """Читает JSON в память. Файл на диске не изменяется."""
    if not path:
        return Node("", "directory"), "VFS в памяти: пустой корень"
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return Node("", "directory"), f"Ошибка загрузки VFS: файл не найден: {path}"
    except json.JSONDecodeError as error:
        return Node("", "directory"), f"Ошибка загрузки VFS: некорректный JSON: {error}"
    if "root" not in data:
        return Node("", "directory"), "Ошибка загрузки VFS: в JSON нет root"
    root = build_node("", data["root"], None)
    root.name = ""
    count = count_nodes(root)
    depth = tree_depth(root)
    return root, f"VFS в памяти: узлов={count}, глубина={depth}"


def count_nodes(node):
    total = 1
    for child in node.children.values():
        total += count_nodes(child)
    return total


def tree_depth(node):
    if not node.children:
        return 1
    return 1 + max(tree_depth(child) for child in node.children.values())


class ShellGUI:
    """Одно окно: сверху журнал, снизу поле ввода."""

    def __init__(self, shell):
        self.shell = shell
        self.root = tk.Tk()
        title = f"Эмулятор - [{shell.username}@{shell.hostname}]"
        self.root.title(title)
        self.root.geometry("800x500")
        self.output = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, font=("Consolas", 12)
        )
        self.output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.entry = tk.Entry(self.root, font=("Consolas", 12))
        self.entry.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.entry.bind("<Return>", self.on_enter)
        self.entry.focus()

    def print_text(self, text):
        self.output.insert(tk.END, text)
        self.output.see(tk.END)

    def show_prompt(self):
        self.print_text(self.shell.prompt())

    def on_enter(self, event=None):
        line = self.entry.get()
        self.entry.delete(0, tk.END)
        self.print_text(line + "\n")
        result = self.shell.execute(line)
        if result:
            self.print_text(result + "\n")
        if self.shell.running:
            self.show_prompt()
        else:
            self.entry.config(state=tk.DISABLED)

    def run_script(self, path):
        try:
            with open(path, encoding="utf-8-sig") as handle:
                text = handle.read()
        except OSError as error:
            self.print_text(f"Ошибка скрипта: {error}\n")
            return
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if not self.shell.running:
                return
            self.print_text(self.shell.prompt() + line + "\n")
            result = self.shell.execute(line)
            if result:
                self.print_text(result + "\n")
        if not self.shell.running:
            self.entry.config(state=tk.DISABLED)


def show_value(value):
    if value:
        return value
    return "не задан"


def main():
    parser = argparse.ArgumentParser(description="Эмулятор UNIX-подобной оболочки")
    parser.add_argument("--vfs", help="Путь к JSON-файлу VFS")
    parser.add_argument("--script", help="Путь к стартовому скрипту")
    args = parser.parse_args()

    root, vfs_note = load_vfs(args.vfs)
    shell = Shell(root)
    gui = ShellGUI(shell)
    gui.print_text("Эмулятор UNIX-подобной командной оболочки\n")
    gui.print_text("Доступные команды: ls, cd, tree, date, exit\n\n")
    gui.print_text(f"[debug] Путь к VFS: {show_value(args.vfs)}\n")
    gui.print_text(f"[debug] Стартовый скрипт: {show_value(args.script)}\n")
    gui.print_text(f"[debug] {vfs_note}\n\n")
    if args.script:
        gui.run_script(args.script)
    if shell.running:
        gui.show_prompt()
    gui.root.mainloop()


if __name__ == "__main__":
    main()
