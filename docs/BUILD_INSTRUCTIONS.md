# LightRAG 服务器打包说明

## 使用现有的 PyInstaller 配置

您的项目中已经有了一个经过验证的 PyInstaller 配置文件 `lightrag-server.spec`，它能够成功打包 LightRAG 服务器。

## 打包步骤

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync
uv add --dev pyinstaller

# 或者使用 pip
pip install -e .
pip install pyinstaller
```

### 2. 执行打包

```bash
# 使用 PyInstaller spec 文件打包
pyinstaller lightrag-server.spec --clean --noconfirm
```

### 3. 运行可执行文件

```bash
# 测试可执行文件
./dist/lightrag-server --help

# 运行服务器
./dist/lightrag-server
```

## 配置特点

现有的 `lightrag-server.spec` 配置文件：
- 使用 `collect_all` 自动收集所有依赖包
- 包含 LightRAG、NumPy、Pandas、SciPy 等核心依赖
- 生成约 58MB 的可执行文件
- 无需修改源代码

## 可选参数

```bash
# 带调试信息的构建
pyinstaller lightrag-server.spec --clean --noconfirm --log-level DEBUG

# 禁用 UPX 压缩（构建更快）
pyinstaller lightrag-server.spec --clean --noconfirm --upx False
```

## 验证

打包成功后，您应该能够在 `dist/` 目录中找到 `lightrag-server` 可执行文件，并且能够正常运行。