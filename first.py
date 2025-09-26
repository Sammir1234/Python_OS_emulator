import shlex
import argparse
import sys
from pathlib import Path

def parse_args():
    p = argparse.ArgumentParser(description="Минималный эмулятор оболочки (REPL)")
    p.add_argument('--vfs', type=str, default='EmulOS', help='Имя виртуальной файловой системы (показывается в приглашении)')
    p.add_argument('--vfs-root', type=str, required=True, help='Путь к физическому расположению VFS')
    p.add_argument('--script', type=str, help='Путь к стартовому скрипту для выполнения команд')
    return p.parse_args()


def ls(args):
    print("ls", "Аргументы:" , args)

def cd(args):
    if len(args) != 1:
        print("cd: неверные аргументы: ожидается ровно 1 аргумент.")
        return 1
    print("cd", "Аргумент:", args[0])

def handle_command(cmd_name, args):
    match cmd_name:
        case 'ls':
            return ls(args)
        case 'cd':
            return cd(args)
        case 'exit':
            exit()
        case _:
            print(f"Ошибка: неизвестная команда: {cmd_name}")
            return 0

def execute_line(line, vfs_name, from_script=False):
    if from_script:
        print(f"{vfs_name} : {line}")

    try:
        tokens = shlex.split(line, posix=True)
    except ValueError as e:
        print(f"Ошибка разбора командной строки: {e}")
        return 1

    if not tokens:
        return 0

    cmd_name, *args = tokens

    if cmd_name == "exit":
        raise SystemExit(0)

    try:
        return handle_command(cmd_name, args)
    except Exception as e:
        print(f"Ошибка выполнения команды {cmd_name}: {e}")
        return 1

def run_script(script_path, vfs_name):
    path = Path(script_path)
    if not path.exists():
        print(f"Ошибка: скрипт {script_path} не найден")
        return 1

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rc = execute_line(line, vfs_name, from_script=True)
            if rc != 0:
                print(f"(строка пропущена из-за ошибки, код {rc})")

def repl_loop(vfs_name):
    while True:
        prompt = f"{vfs_name}: "
        raw = input(prompt)
        tokens = shlex.split(raw, posix=True)
        cmd_name, *args = tokens
        rc = handle_command(cmd_name, args)
        

opts = parse_args()

print("=== Параметры запуска эмулятора ===")
print(f"Имя VFS:       {opts.vfs}")
print(f"Физический VFS: {opts.vfs_root}")
print(f"Стартовый скрипт: {opts.script if opts.script else '(не задан)'}")
print("===================================")

if opts.script:
    run_script(opts.script, opts.vfs)

repl_loop(opts.vfs)


    
