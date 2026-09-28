import os
import socket
import shlex
import tkinter as tk
from tkinter import scrolledtext


class Shell:
    def __init__(self):
        self.username = os.environ.get("USERNAME",os.environ.get("USER", "user"))
        self.hostname = socket.gethostname()
        self.running = True

    def prompt(self):
        return f"{self.username}@{self.hostname}$ "

    def parse(self, line):
        line = os.path.expandvars(line)
        return shlex.split(line)

    def execute(self, line):
        line = line.strip()
        if not line:
            return ""
        try:
            args = self.parse(line)
        except ValueError as error:
            return f"Ошибка разбора команды: {error}"
        if not args:
            return ""
        command = args[0]
        command_args = args[1:]
        if command == "ls":
            if command_args:
                return "ls: " + " ".join(command_args)
            return "ls"
        elif command == "cd":
            if command_args:
                return "cd: " + " ".join(command_args)
            return "cd"
        elif command == "exit":
            if command_args:
                return "Ошибка: exit не принимает аргументы"
            self.running = False
            return "Выход из эмулятора."
        else:
            return f"Ошибка: неизвестная команда '{command}'"


class ShellGUI:

    def __init__(self, shell):
        self.shell = shell
        self.root = tk.Tk()
        self.root.title(f"Эмулятор - "f"[{shell.username}@{shell.hostname}]")
        self.root.geometry("800x500")
        self.output = scrolledtext.ScrolledText(self.root, wrap=tk.WORD,font=("Arial", 12))
        self.output.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        self.entry = tk.Entry(
            self.root,
            font=("Arial", 12)
        )

        self.entry.pack(
            fill=tk.X,
            padx=10,
            pady=(0, 10)
        )

        self.entry.bind(
            "<Return>",
            self.on_enter
        )

        self.print_text("Эмулятор UNIX-подобной командной оболочки\n")
        self.print_text("Доступные команды: ls, cd, exit\n\n")
        self.show_prompt()
        self.entry.focus()

    def print_text(self, text):
        self.output.insert(tk.END,text)
        self.output.see(tk.END)

    def show_prompt(self):
        self.print_text(self.shell.prompt())

    def on_enter(self, event=None):
        line = self.entry.get()
        self.entry.delete(0,tk.END)
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