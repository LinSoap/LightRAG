# PyInstaller打包任务列表

## 目标
将LightRAG服务打包成可执行文件，支持在Electron中直接启动，无需Python环境。

## 任务概览
- 依赖分析和打包配置
- 资源文件处理
- 跨平台打包支持
- Electron集成测试

## 🔴 任务1：依赖分析和打包配置

### 问题
- LightRAG项目依赖复杂（numpy、fastapi、uvicorn等）
- 动态导入和隐藏模块处理
- 资源文件和数据文件打包

### 目标
- 创建PyInstaller配置文件
- 解决所有依赖导入问题
- 确保打包后的可执行文件正常工作

### 交付物
- [ ] 创建PyInstaller spec配置文件
- [ ] 分析所有依赖模块（hidden-imports）
- [ ] 解决numpy、pandas等C扩展模块问题
- [ ] 配置资源文件打包（data files、binaries）
- [ ] 创建打包脚本（build.py）

### 技术细节
- 使用 `pyi-makespec` 生成基础配置
- 添加所有hidden-imports
- 配置数据文件打包路径
- 设置控制台/窗口模式选项

## 🔴 任务2：资源文件处理

### 问题
- LightRAG有存储目录和配置文件
- 需要处理运行时资源路径
- 确保打包后仍能找到资源文件

### 目标
- 正确打包静态资源文件
- 实现运行时路径检测
- 支持用户数据目录分离

### 交付物
- [ ] 分析项目中的资源文件需求
- [ ] 配置PyInstaller的--add-data参数
- [ ] 修改代码以支持打包后的资源路径
- [ ] 实现资源路径自动检测机制
- [ ] 测试资源文件访问

### 技术细节
- 使用 `sys._MEIPASS` 获取打包后的资源路径
- 修改路径管理器以支持打包环境
- 确保配置文件和模板文件正确打包

## 🔴 任务3：跨平台打包支持

### 问题
- 需要支持Windows、macOS、Linux三个平台
- 不同平台的打包配置不同
- 文件扩展名和路径分隔符差异

### 目标
- 创建跨平台打包脚本
- 自动适配不同平台的配置
- 生成对应平台的可执行文件

### 交付物
- [ ] 创建平台检测脚本
- [ ] 配置Windows打包设置（.exe文件）
- [ ] 配置macOS打包设置（可执行文件）
- [ ] 配置Linux打包设置（可执行文件）
- [ ] 创建自动化打包脚本
- [ ] 测试各平台生成的可执行文件

### 技术细节
- 处理不同平台的文件扩展名
- 配置平台特定的运行时选项
- 设置合适的图标和元数据

## 🔴 任务4：Electron集成优化

### 问题
- Electron中需要智能识别开发/生产环境
- 可执行文件路径定位
- 参数传递和进程管理

### 目标
- 实现开发环境和生产环境的无缝切换
- 优化Electron中的服务启动逻辑
- 确保稳定性和错误处理

### 交付物
- [ ] 修改Electron主进程服务启动逻辑
- [ ] 实现智能可执行文件路径检测
- [ ] 添加打包文件的版本管理
- [ ] 创建服务启动的封装函数
- [ ] 实现优雅的错误处理和日志记录
- [ ] 编写集成测试用例

### 技术细节
- 使用 `app.isPackaged` 检测运行环境
- 实现可执行文件的自动定位
- 添加进程监控和自动重启机制

## 🔴 任务5：测试和验证

### 问题
- 确保打包后的功能完整性
- 验证所有参数和配置正常工作
- 性能和稳定性测试

### 目标
- 全面测试打包后的可执行文件
- 验证与Electron的集成
- 确保用户体验一致

### 交付物
- [ ] 创建完整的功能测试清单
- [ ] 测试所有命令行参数
- [ ] 验证健康检查功能
- [ ] 测试存储路径配置
- [ ] 验证Electron集成效果
- [ ] 性能对比测试（打包vs Python模块）
- [ ] 用户接受度测试

### 技术细节
- 自动化测试脚本
- 错误场景模拟
- 长时间运行稳定性测试

## 技术实现细节

### PyInstaller基础配置
```python
# lightrag-server.spec
block_cipher = None

a = Analysis(
    ['lightrag/api/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('lightrag', 'lightrag'),  # 包含lightrag包
        ('configs', 'configs'),    # 配置文件
    ],
    hiddenimports=[
        'lightrag.utils.path_manager',
        'lightrag.utils.path_config',
        'lightrag.api.health_checker',
        'lightrag.api.service_manager',
        'numpy',
        'pandas',
        'fastapi',
        'uvicorn',
        # ... 更多依赖
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyi = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyi,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='lightrag-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 设置为False可隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### 打包脚本
```python
# scripts/build.py
import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_lightrag_server():
    """构建LightRAG服务器可执行文件"""
    print("🔨 开始构建LightRAG服务器...")

    # 清理之前的构建
    build_dir = Path("build")
    dist_dir = Path("dist")
    for dir_path in [build_dir, dist_dir]:
        if dir_path.exists():
            shutil.rmtree(dir_path)

    # 运行PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name=lightrag-server",
        "--specpath=scripts",
        "--workpath=build",
        "--distpath=dist",
        "--add-data=lightrag;lightrag",
        "--hidden-import=lightrag.utils.path_manager",
        "--hidden-import=lightrag.utils.path_config",
        "--hidden-import=lightrag.api.health_checker",
        "--hidden-import=lightrag.api.service_manager",
        "lightrag/api/main.py"
    ]

    try:
        subprocess.run(cmd, check=True)
        print("✅ 构建成功！可执行文件位于 dist/lightrag-server")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        return False

if __name__ == "__main__":
    build_lightrag_server()
```

### Electron集成代码
```javascript
// electron主进程
const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

class LightRAGService {
    constructor() {
        this.serviceProcess = null;
        this.servicePort = null;
    }

    getExecutablePath() {
        if (app.isPackaged) {
            // 生产环境：使用打包的可执行文件
            const platform = process.platform;
            const ext = platform === 'win32' ? '.exe' : '';
            return path.join(process.resourcesPath, 'bin', `lightrag-server${ext}`);
        } else {
            // 开发环境：使用Python模块
            return 'python';
        }
    }

    getServiceArgs() {
        const userDataPath = app.getPath('userData');
        const storageDir = path.join(userDataPath, 'lightrag-data');

        const baseArgs = [
            '--port', '0',
            '--storage-dir', storageDir,
            '--workspace', 'default',
            '--log-level', app.isPackaged ? 'warning' : 'debug'
        ];

        if (!app.isPackaged) {
            // 开发环境需要添加模块路径
            return ['-m', 'lightrag.api.main', ...baseArgs];
        }

        return baseArgs;
    }

    async start() {
        const executable = this.getExecutablePath();
        const args = this.getServiceArgs();

        console.log(`🚀 启动LightRAG服务: ${executable} ${args.join(' ')}`);

        this.serviceProcess = spawn(executable, args);

        this.serviceProcess.stdout.on('data', (data) => {
            const output = data.toString();
            console.log(`[LightRAG] ${output}`);

            // 解析端口信息
            const portMatch = output.match(/LightRAG 服务启动在自动选择的端口: (\d+)/);
            if (portMatch) {
                this.servicePort = parseInt(portMatch[1]);
                console.log(`✅ LightRAG服务已启动，端口: ${this.servicePort}`);
                this.emit('started', { port: this.servicePort });
            }
        });

        this.serviceProcess.stderr.on('data', (data) => {
            console.error(`[LightRAG Error] ${data.toString()}`);
        });

        this.serviceProcess.on('close', (code) => {
            console.log(`LightRAG服务已关闭，退出码: ${code}`);
            this.serviceProcess = null;
            this.servicePort = null;
        });
    }

    async stop() {
        if (this.serviceProcess) {
            this.serviceProcess.kill('SIGTERM');
            // 等待优雅关闭
            await new Promise(resolve => setTimeout(resolve, 5000));
            if (this.serviceProcess) {
                this.serviceProcess.kill('SIGKILL');
            }
        }
    }

    getApiUrl(endpoint = '') {
        if (!this.servicePort) {
            throw new Error('服务未启动');
        }
        return `http://127.0.0.1:${this.servicePort}/${endpoint}`;
    }
}
```

## 预估时间安排

- **任务1：依赖分析和打包配置** - 2-3天
- **任务2：资源文件处理** - 1-2天
- **任务3：跨平台打包支持** - 2-3天
- **任务4：Electron集成优化** - 1-2天
- **任务5：测试和验证** - 2天

**总预估时间：8-12天**

## 下一步行动

1. **立即开始**：任务1 - 依赖分析和打包配置
2. **优先级**：任务1 → 任务2 → 任务4 → 任务3 → 任务5
3. **测试策略**：每个任务完成后立即在对应平台测试

## 注意事项

1. **备份重要**：打包前确保代码已提交到版本控制
2. **渐进式开发**：先实现基础功能，再逐步完善
3. **多平台测试**：确保在目标平台上进行充分测试
4. **文档更新**：完成后更新Electron集成解决方案文档
5. **版本管理**：考虑可执行文件的版本控制和更新机制