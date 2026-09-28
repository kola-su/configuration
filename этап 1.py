import os
import socket
import shlex
import tkinter as tk
from tkinter import scrolledtext


class Shell:
    """Класс командной оболочки для обработки пользовательских команд."""

    def __init__(self):
        """Инициализирует оболочку, определяет имя пользователя и компьютера."""
        self.username = os.environ.get("USERNAME", os.environ.get("USER", "user"))
        self.hostname = socket.gethostname()
        self.running = True

    def prompt(self):
        """Формирует приглашение командной строки с именем пользователя и компьютера."""
        return f"{self.username}@{self.hostname}$ "

    def parse(self, line):
        """Обрабатывает строку команды, подставляет переменные окружения и разделяет аргументы."""
        line = os.path.expandvars(line)
        return shlex.split(line)

    def execute(self, line):
        """Обрабатывает введённую команду и возвращает результат или сообщение об ошибке.

        Поддерживает команды ls, cd и exit. Команды ls и cd выводят своё название
        и переданные аргументы. Команда exit завершает работу оболочки при отсутствии
        дополнительных аргументов.
        """
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
    """Класс графического интерфейса эмулятора командной оболочки."""

    def __init__(self, shell):
        """Создаёт окно программы, область вывода и поле ввода команд.

        Args:
            shell: Объект командной оболочки для обработки введённых команд.
        """
        self.shell = shell
        self.root = tk.Tk()
        self.root.title(f"Эмулятор - [{shell.username}@{shell.hostname}]")
        self.root.geometry("800x500")
        self.output = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Arial", 12)
        )
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
        """Выводит переданный текст в окно программы и прокручивает его вниз.

        Args:
            text: Строка для отображения в области вывода.
        """
        self.output.insert(tk.END, text)
        self.output.see(tk.END)

    def show_prompt(self):
        """Отображает приглашение командной строки."""
        self.print_text(self.shell.prompt())

    def on_enter(self, event=None):
        """Обрабатывает нажатие Enter, выполняет команду и выводит результат.

        После завершения работы оболочки отключает поле ввода.

        Args:
            event: Событие Tkinter, связанное с нажатием клавиши Enter.
        """
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
    """Создаёт командную оболочку и запускает графический интерфейс."""
    shell = Shell()
    gui = ShellGUI(shell)
    gui.root.mainloop()


if __name__ == "__main__":
    main()