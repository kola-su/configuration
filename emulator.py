import os
import shlex
import socket
import tkinter as tk
from tkinter import scrolledtext


class Shell:
    def __init__(self):
        self.username = os.environ.get("USERNAME", os.environ.get("USER", "user"))
        self.hostname = socket.gethostname()
        self.running = True

    def prompt(self):
        return f"{self.username}@{self.hostname}$ "

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
        self.print_text("Эмулятор UNIX-подобной командной оболочки\n")
        self.print_text("Доступные команды: ls, cd, exit\n\n")
        self.show_prompt()
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


def main():
    shell = Shell()
    gui = ShellGUI(shell)
    gui.root.mainloop()


if __name__ == "__main__":
    main()
