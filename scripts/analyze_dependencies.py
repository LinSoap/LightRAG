#!/usr/bin/env python3
"""
LightRAG依赖分析脚本
用于分析LightRAG项目的所有依赖，为PyInstaller打包提供准确的hidden-imports列表
"""

import os
import sys
import ast
import importlib
from pathlib import Path
from typing import Set, Dict, List, Tuple

class DependencyAnalyzer(ast.NodeVisitor):
    """AST节点访问器，用于分析Python文件中的导入"""

    def __init__(self):
        self.imports: Set[str] = set()
        self.from_imports: Dict[str, Set[str]] = {}

    def visit_Import(self, node: ast.Import):
        """处理import语句"""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """处理from ... import语句"""
        if node.module:
            if node.module not in self.from_imports:
                self.from_imports[node.module] = set()
            for alias in node.names:
                self.from_imports[node.module].add(alias.name)
        self.generic_visit(node)

def analyze_file(file_path: Path) -> Tuple[Set[str], Dict[str, Set[str]]]:
    """分析单个Python文件的导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)
        analyzer = DependencyAnalyzer()
        analyzer.visit(tree)

        return analyzer.imports, analyzer.from_imports
    except Exception as e:
        print(f"分析文件 {file_path} 时出错: {e}")
        return set(), {}

def find_python_files(directory: Path) -> List[Path]:
    """递归查找所有Python文件"""
    python_files = []

    # 跳过的目录
    skip_dirs = {'__pycache__', '.git', 'venv', '.venv', 'build', 'dist', 'node_modules'}

    for file_path in directory.rglob('*.py'):
        # 跳过测试文件和临时文件
        if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
            continue
        if 'test' in file_path.name.lower():
            continue

        python_files.append(file_path)

    return python_files

def check_package_availability(package_name: str) -> bool:
    """检查包是否可用"""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def categorize_imports(all_imports: Set[str]) -> Dict[str, List[str]]:
    """将导入分类"""
    categories = {
        'standard_library': [],
        'third_party': [],
        'local': [],
        'unknown': []
    }

    # 标准库列表（常见的一些）
    stdlib_modules = {
        'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 'logging', 'argparse',
        'asyncio', 'subprocess', 'threading', 'multiprocessing', 'signal',
        'atexit', 'gc', 'inspect', 'traceback', 'warnings', 'typing',
        'dataclasses', 'enum', 'collections', 'itertools', 'functools',
        'contextlib', 'tempfile', 'shutil', 'glob', 'fnmatch',
        'socket', 'urllib', 'http', 'email', 'sqlite3', 'xml', 'html',
        'csv', 'configparser', 'pickle', 'base64', 'hashlib', 'hmac',
        'random', 'secrets', 'math', 'statistics', 'decimal',
        'io', 'struct', 'array', 'bisect', 'heapq', 'queue', 'weakref',
        'copy', 'pprint', 're', 'string', 'unicodedata', 'codecs',
        'encodings', 'locale', 'datetime', 'calendar', 'time',
        'zoneinfo', 'threading', 'multiprocessing', 'concurrent',
        'asyncio', 'curio', 'trio', 'unittest', 'doctest', 'pdb',
        'profile', 'cProfile', 'timeit', 'trace', 'gc', 'weakref',
        'abc', 'numbers', 'types', 'copyreg', 'pickletools',
    }

    for imp in all_imports:
        if imp.split('.')[0] in stdlib_modules:
            categories['standard_library'].append(imp)
        elif imp.startswith('lightrag'):
            categories['local'].append(imp)
        elif check_package_availability(imp.split('.')[0]):
            categories['third_party'].append(imp)
        else:
            categories['unknown'].append(imp)

    return categories

def generate_hidden_imports(local_imports: List[str]) -> List[str]:
    """生成PyInstaller的hidden-imports列表"""
    hidden_imports = []

    for imp in local_imports:
        # 添加lightrag包的所有模块
        if imp.startswith('lightrag.'):
            hidden_imports.append(imp)

    # 添加一些常见的需要显式声明的第三方库
    common_hidden = [
        'numpy',
        'pandas',
        'fastapi',
        'uvicorn',
        'psutil',
        'networkx',
        'pydantic',
        'httpx',
        'aiofiles',
        'python_multipart',
        'json_repair',
        'nano_vectordb',
        'pypinyin',
        'tqdm',
        'tenacity',
        'tiktoken',
        'openai',
        'dotenv',
        'yaml',
        'scipy',
        'sklearn',
    ]

    for item in common_hidden:
        if item not in hidden_imports and check_package_availability(item):
            hidden_imports.append(item)

    return hidden_imports

def main():
    """主函数"""
    print("🔍 开始分析LightRAG依赖...")

    # 项目根目录
    project_root = Path(__file__).parent.parent
    lightrag_dir = project_root / 'lightrag'

    if not lightrag_dir.exists():
        print(f"❌ 找不到lightrag目录: {lightrag_dir}")
        return

    # 查找所有Python文件
    print("📁 查找Python文件...")
    python_files = find_python_files(lightrag_dir)
    print(f"📄 找到 {len(python_files)} 个Python文件")

    # 分析所有文件
    print("📊 分析导入语句...")
    all_imports = set()
    all_from_imports = {}

    for file_path in python_files:
        imports, from_imports = analyze_file(file_path)
        all_imports.update(imports)

        for module, names in from_imports.items():
            if module not in all_from_imports:
                all_from_imports[module] = set()
            all_from_imports[module].update(names)

    # 合并所有导入
    for module, names in all_from_imports.items():
        all_imports.add(module)
        # 为一些常见的模式添加子模块
        if module == 'lightrag.utils':
            all_imports.add('lightrag.utils.path_manager')
            all_imports.add('lightrag.utils.path_config')

    print(f"🔢 总共发现 {len(all_imports)} 个不同的导入")

    # 分类导入
    categories = categorize_imports(all_imports)

    print("\n📋 依赖分类:")
    print(f"  标准库: {len(categories['standard_library'])} 个")
    print(f"  第三方库: {len(categories['third_party'])} 个")
    print(f"  本地模块: {len(categories['local'])} 个")
    print(f"  未知模块: {len(categories['unknown'])} 个")

    # 生成hidden-imports
    hidden_imports = generate_hidden_imports(categories['local'] + categories['third_party'])

    print(f"\n🎯 建议的hidden-imports列表 ({len(hidden_imports)} 个):")
    for imp in sorted(hidden_imports):
        print(f"  - {imp}")

    # 如果有未知模块，显示警告
    if categories['unknown']:
        print(f"\n⚠️  未知模块 ({len(categories['unknown'])} 个):")
        for imp in categories['unknown']:
            print(f"  - {imp}")

    # 生成PyInstaller命令
    print(f"\n🔨 建议的PyInstaller命令:")
    hidden_args = ' '.join([f'--hidden-import={imp}' for imp in hidden_imports])
    print(f"pyinstaller --onefile --name lightrag-server {hidden_args} lightrag/api/main.py")

    # 保存结果到文件
    result = {
        'hidden_imports': hidden_imports,
        'categories': categories,
        'total_files': len(python_files),
        'total_imports': len(all_imports)
    }

    import json
    with open(project_root / 'scripts' / 'dependency_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n💾 分析结果已保存到: scripts/dependency_analysis.json")

if __name__ == '__main__':
    main()