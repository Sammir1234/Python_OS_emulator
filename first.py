import shlex
import argparse
import sys

def parse_args():
    p = argparse.ArgumentParser(description="Минималный эмулятор оболочки (REPL)")
    p.add_argument('--vfs', type=str, default='VFS', help='Имя виртуальной файловой системы (показывается в приглашении)')
    return p.parse_args()

def ls(args):
    print("ls", "Аргументы:" , args)
    return 0

def cd(args):
    if len(args) != 1:
        print("cd: неверные аргументы: ожидается ровно 1 аргумент.")
        return 1
    print("cd", "Аргумент:", args[0])
    return 0

def handle_command(cmd_name, args):
    match cmd_name:
        case 'ls':
            return ls(args)
        case 'cd':
            return cd(args)
        case 'exit':
            exit()
        case '':
            return 0
        case _:
            print(f"Ошибка: неизвестная команда: {cmd_name}")
            return 0

def repl_loop(vfs_name):
    while True:
        prompt = f"{vfs_name}: "
        raw = input(prompt)
        tokens = shlex.split(raw, posix=True)
        cmd_name, *args = tokens
        rc = handle_command(cmd_name, args)
        

opts = parse_args()
repl_loop(opts.vfs)


    
