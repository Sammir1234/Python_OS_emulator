import shlex
import argparse
import sys
from pathlib import Path
import base64
import zipfile
import io
import time

#---------VFS--------
class Node:
    def __init__(self, name, is_dir):
        self.name = name
        self.is_dir = is_dir
        self.children = {}
        self.content = None

    def add_child(self, node):
        self.children[node.name] = node

class VFS:
    def __init__(self):
        self.root = Node("/", True)

    def load_from_zip_bytes(self, zip_bytes):
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except zipfile.BadZipFile:
            raise ValueError("Файл не является корректным ZIP-архивом.")
        except Exception as e:
            raise ValueError(f"Ошибка при открытии ZIP: {e}")

        for info in zf.infolist():
            path = info.filename
            if path.endswith("/"):
                components = [c for c in path.strip("/").split("/") if c]
                self._ensure_dirs(components)
            else:
                components = [c for c in path.strip("/").split("/") if c]
                parent = self._ensure_dirs(components[:-1])
                data = zf.read(info.filename)
                fname = components[-1]
                file_node = Node(fname, False)
                file_node.content = data
                parent.children[fname] = file_node

    def _ensure_dirs(self, components):
        node = self.root
        for comp in components:
            if comp not in node.children:
                nd = Node(comp, True)
                node.children[comp] = nd
            node = node.children[comp]
            if not node.is_dir:
                raise ValueError(f"Невозможно создать каталог '{comp}': файл с таким именем уже существует")
        return node

    def get_node(self, path_components):
        node = self.root
        for comp in path_components:
            if comp == "" or comp == ".":
                continue
            if comp == "..":
                continue
            if comp not in node.children:
                return None
            node = node.children[comp]
        return node
#-------Состояние оболочки-----
class ShellState:
    def __init__(self, vfs_name="EmulOS"):
        self.vfs_name = vfs_name
        self.vfs = None
        self.cwd = []
        self.start_time = time.time()

    def set_vfs(self, vfs):
        self.vfs = vfs
        self.cwd = []

    def canonical_path_components(self, path):
        if path.startswith("/"):
            comps = [c for c in path.strip("/").split("/") if c]
            base = []
        else:
            comps = [c for c in path.split("/") if c]
            base = list(self.cwd)
        for c in comps:
            if c == ".":
                continue
            if c == "..":
                if base:
                    base.pop()
            else:
                base.append(c)
        return base
#--------Команды----------
def ls(state: ShellState, args):
    if len(args) > 1:
        print("ls: неверные аргументы: ожидается 0 или 1 аргумент")
        return 1
    if args:
        comps = state.canonical_path_components(args[0])
    else:
        comps = list(state.cwd)
    node = state.vfs.get_node(comps)
    if node is None:
        print("ls: путь не найден")
        return 1
    if not node.is_dir:
        print(node.name)
        return 0
    for name, child in sorted(node.children.items()):
        suffix = "/" if child.is_dir else ""
        print(name + suffix)
    return 0

def cd(state: ShellState, args):
    if len(args) != 1:
        print("cd: неверные аргументы: ожидается ровно 1 аргумент.")
        return 1
    comps = state.canonical_path_components(args[0])
    node = state.vfs.get_node(comps)
    if node is None:
        print("cd: путь не найден")
        return 1
    if not node.is_dir:
        print("cd: не каталог")
        return 1
    state.cwd = comps
    return 0
def cat(state: ShellState, args):
    if not args:
        print("cat: требуется имя файла")
        return 1
    use_b64 = False
    if args[0] == "--base64":
        use_b64 = True
        args = args[1:]
    if len(args) != 1:
        print("cat: требуется ровно 1 имя файла")
        return 1
    comps = state.canonical_path_components(args[0])
    node = state.vfs.get_node(comps)
    if node is None or node.is_dir:
        print("cat: файл не найден или это каталог")
        return 1
    if use_b64:
        print(base64.b64decode(node.content).decode())
    else:
        try:
            print(node.content.decode("utf-8"), end="" + "\n")
        except:
            print(base64.b64decode(node.content).decode())
    return 0

def uname(state: ShellState, args):
    print(f"{state.vfs_name} 1.4")
    return 0

def uptime(state: ShellState, args):
    seconds = int(time.time() - state.start_time)
    print(f"Время работы системы: {seconds} сек.")
    return 0

def mv(state: ShellState, args):
    if len(args) != 2:
        print("mv: требуется 2 аргумента: источник и назначение")
        return 1

    src, dest = args
    src_comps = state.canonical_path_components(src)
    dest_comps = state.canonical_path_components(dest)

    # Найти исходный узел и его родителя
    src_parent = state.vfs.get_node(src_comps[:-1])
    src_name = src_comps[-1]
    if src_parent is None or src_name not in src_parent.children:
        print(f"mv: исходный файл не найден: {src}")
        return 1
    src_node = src_parent.children[src_name]

    # Определяем, куда перемещаем
    dest_parent = state.vfs.get_node(dest_comps[:-1])
    dest_name = dest_comps[-1]

    if dest_parent is None:
        print(f"mv: каталог назначения не найден: {'/'.join(dest_comps[:-1])}")
        return 1

    dest_node = state.vfs.get_node(dest_comps)
    if dest_node and dest_node.is_dir: #Если dest - каталог
        #Переместить внутрь каталога
        new_parent = dest_node
        new_name = src_name
    else:
        #Переименование/перемещение
        new_parent = dest_parent
        new_name = dest_name

    #Запрет перемещения папки в саму себя
    if src_node.is_dir and new_parent == src_node:
        print(f"mv: нельзя переместить каталог в самого себя: {src}")
        return 1

    #Перемещение
    del src_parent.children[src_name]
    src_node.name = new_name
    new_parent.children[new_name] = src_node
    return 0

def touch(state: ShellState, args):
    if len(args) != 1:
        print("touch: требуется ровно 1 аргумент")
        return 1

    path = args[0]
    comps = state.canonical_path_components(path)
    parent = state.vfs.get_node(comps[:-1])
    fname = comps[-1]

    if parent is None:
        print(f"touch: путь не найден: {'/'.join(comps[:-1])}")
        return 1
    if not parent.is_dir:
        print(f"touch: {path}: не каталог")
        return 1

    if fname in parent.children:
        node = parent.children[fname]
        if node.is_dir:
            print(f"touch: {path}: это каталог")
            return 1
        # Файл уже существует — ничего не делаем
        return 0
    else:
        new_file = Node(fname, False)
        new_file.content = b""
        parent.children[fname] = new_file
        return 0

def handle_command(state: ShellState, cmd_name, args):
    match cmd_name:
        case 'ls': return ls(state, args)
        case 'cd': return cd(state, args)
        case 'cat': return cat(state, args)
        case 'uname': return uname(state, args)
        case 'uptime': return uptime(state, args)
        case 'mv': return mv(state, args)
        case 'touch': return touch(state, args)
        case 'exit': raise SystemExit(0)
        case '': return 0
        case _: 
            print(f"Ошибка: неизвестная команда: {cmd_name}")
            return 127
#------Выполнение------
def execute_line(state: ShellState, line, from_script=False):
    if from_script:
        print(f"{state.vfs_name} $ {line}")
    try:
        tokens = shlex.split(line, posix=True)
    except ValueError as e:
        print(f"Ошибка парсинга: {e}")
        return 1
    if not tokens:
        return 0
    cmd, *args = tokens
    try:
        return handle_command(state, cmd, args)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Ошибка выполнения {cmd}: {e}")
        return 1

def run_script(state: ShellState, script_path):
    path = Path(script_path)
    if not path.exists():
        print(f"Ошибка: скрипт {script_path} не найден")
        return 1
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rc = execute_line(state, line, from_script=True)
            if rc != 0:
                print(f"(строка пропущена из-за ошибки, код {rc})")

def repl_loop(state: ShellState):
    while True:
        try:
            raw = input(f"{state.vfs_name} $ ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue
        if not raw.strip():
            continue
        execute_line(state, raw)
        
#-----------Main-----------
def parse_args():
    p = argparse.ArgumentParser(description="Минималный эмулятор оболочки (REPL)")
    p.add_argument('--vfs', type=str, default='EmulOS', help='Имя виртуальной файловой системы (показывается в приглашении)')
    p.add_argument('--vfs-root', type=str, required=True, help='Путь к физическому расположению VFS')
    p.add_argument('--script', type=str, help='Путь к стартовому скрипту для выполнения команд')
    return p.parse_args()

def load_vfs(zip_path):
    p = Path(zip_path)
    if not p.exists():
        raise FileNotFoundError(f"ZIP-файл VFS не найден: {zip_path}")
    try:
        b = p.read_bytes()
    except Exception as e:
        raise IOError(f"Ошибка чтения файла {zip_path}: {e}")
    vfs = VFS()
    vfs.load_from_zip_bytes(b)
    return vfs

opts = parse_args()

print("=== Параметры запуска эмулятора ===")
print(f"Имя VFS:       {opts.vfs}")
print(f"Физический VFS: {opts.vfs_root}")
print(f"Стартовый скрипт: {opts.script if opts.script else '(не задан)'}")
print("===================================")

state = ShellState(opts.vfs)

try:
    vfs = load_vfs(opts.vfs_root)
except Exception as e:
    print("Ошибка загрузки VFS:", e)
    sys.exit(2)

state.set_vfs(vfs)

if opts.script:
    run_script(state, opts.script)

repl_loop(state)

    
