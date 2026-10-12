import argparse
import base64
import json
import os
import shlex
import socket
import tkinter as tk
from tkinter import scrolledtext


class Node:
    def __init__(self, name, kind):
        self.name = name
        self.kind = kind
        self.content = b""
        self.children = {}
        self.parent = None

    def is_dir(self):
        return self.kind == "directory"


class Shell:
    def __init__(self, root=None):
        self.username = os.environ.get("USERNAME", os.environ.get("USER", "user"))
        self.hostname = socket.gethostname()
        self.running = True
        self.root = root or Node("", "directory")
        self.cwd = self.root

    def prompt(self):
        return f"{self.username}@{self.hostname}:{self.abs_path(self.cwd)}$ "

    def abs_path(self, node):
        if node.parent is None:
            return "/"
        names = []
        current = node
        while current.parent is not None:
            names.append(current.name)
            current = current.parent
        return "/" + "/".join(reversed(names))

    def expand(self, line):
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
            if rest:
                return "ls: " + " ".join(rest)
            return "ls"
        if command == "cd":
            if rest:
                return "cd: " + " ".join(rest)
            return "cd"
        if command == "exit":
            if rest:
                return "Ошибка: exit не принимает аргументы"
            self.running = False
            return "Выход из эмулятора."
        return f"Ошибка: неизвестная команда '{command}'"


class ShellGUI:
    def __init__(self, shell):
        self.shell = shell
        self.root = tk.Tk()
        self.root.title(f"Эмулятор - [{shell.username}@{shell.hostname}]")
        self.root.geometry("800x500")
        self.output = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, font=("Arial", 12)
        )
        self.output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.entry = tk.Entry(self.root, font=("Arial", 12))
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
    return root, f"VFS в памяти: узлов={count_nodes(root)}, глубина={tree_depth(root)}"


def count_nodes(node):
    total = 1
    for child in node.children.values():
        total += count_nodes(child)
    return total


def tree_depth(node):
    if not node.children:
        return 1
    return 1 + max(tree_depth(child) for child in node.children.values())


def show_value(value):
    if value:
        return value
    return "не задан"


def main():
    parser = argparse.ArgumentParser(description="Эмулятор UNIX-подобной оболочки")
    parser.add_argument("--vfs", help="Путь к JSON-файлу VFS")
    parser.add_argument("--script", help="Путь к стартовому скрипту")
    args = parser.parse_args()
    root, note = load_vfs(args.vfs)
    shell = Shell(root)
    gui = ShellGUI(shell)
    gui.print_text("Эмулятор UNIX-подобной командной оболочки\n")
    gui.print_text("Доступные команды: ls, cd, exit\n\n")
    gui.print_text(f"[debug] Путь к VFS: {show_value(args.vfs)}\n")
    gui.print_text(f"[debug] Стартовый скрипт: {show_value(args.script)}\n")
    gui.print_text(f"[debug] {note}\n\n")
    if args.script:
        gui.run_script(args.script)
    if shell.running:
        gui.show_prompt()
    gui.root.mainloop()


if __name__ == "__main__":
    main()
