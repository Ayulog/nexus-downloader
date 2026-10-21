# 中文桌面版

基于 Samxel/nexus-downloader 的 Tkinter GUI。新增界面由 Ayulog 维护，原项目版权与 MIT 许可保留。

## 便携 EXE 版（推荐）

从本仓库 GitHub Releases 下载 `NexusDownloader-v0.1.0-windows-x64.zip`，完整解压后双击 **NexusDownloader.exe**，无需安装 Python。请保留同目录的 **NexusDownloaderWorker.exe**，它是界面调用的后台下载程序。

配置、链接和默认下载目录保存在 EXE 所在目录；请解压到可写目录。不要在 ZIP 预览中直接运行。OAuth 会话仍沿用原项目的用户目录文件。

## 从源码启动

Windows 下双击 **Start-GUI.cmd**。首次运行会调用 **Setup-GUI.cmd** 安装项目依赖。
需要 Python 3.11+（包含 Tcl/Tk）或已安装 `uv`；如果现有 Python 缺少 Tk，安装脚本会通过 uv 在项目的 `.python/` 内准备 Python 3.12。环境和依赖只放在项目目录。

也可以手动运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe gui.py
```

## 布局与文件位置

窗口会随宽度在左右两栏、上下单栏之间切换；内容过高时可用滚动条或空白区域上的滚轮查看。底部开始、停止、保存和打开目录按钮固定显示，窄窗口或较高系统缩放下会自动换行。

压缩包只套一层游戏目录，例如：

```text
downloads/
  stardewvalley/
    963-12345-original-mod-name.zip
    9999-23456-another-mod.7z
```

文件名前的 MOD ID 与文件 ID 用于避免同名覆盖。开启解压时，每个压缩包的内容仍解压到独立子目录。旧版已生成的 MOD 子目录不自动移动或删除；新下载使用上述布局。

## 使用

1. 粘贴 Nexus MOD 页面链接，每行一个；或导入 UTF-8 编码的 TXT 文件。重复链接会自动去重，错误行会在启动前指出。
2. 选择下载目录、并行数量，以及是否自动解压。相对目录以项目目录为基准。
3. 登录 Nexus 网站，在浏览器开发者工具的 Application / Storage → Cookies 中复制 **nexusmods_session**，填入窗口的 Cookie 输入框。
4. 点击 **浏览器登录 / 验证** 完成原项目的 OAuth 授权。这个授权与上面的 Cookie 是两套凭据，两者都需要；界面不自动提取浏览器 Cookie。开始下载也会自动验证授权。
5. 点击 **开始下载**。窗口显示扫描数量、传输字节、当前文件速度与进度，以及成功、跳过、失败计数。完整日志仍由原下载器写入配置的日志目录。

**停止**会请求后台退出并清理 `.part` 文件。正在进行的网络请求会等到返回或超时，正在解压的文件会等解压结束。关闭正在工作的窗口也会先停止任务，再退出，不会直接杀死解压过程。停止后再次开始会跳过已完成文件，未完成文件重新下载，不支持字节级断点续传。

设置并行数量时，队列容量会同步提高到至少该数量，避免隐藏的队列上限限制并行下载。

窗口保存常用配置时会保留 `config.toml` 中的高级选项和注释。Cookie 以原项目方式明文保存在本机 `config.toml`（已被 Git 忽略）；OAuth 会话使用原项目的用户目录会话文件。不要分享这些文件。链接保存在配置指定的 `mod_list` 中。

高级设置仍可编辑 `config.toml`：文件分类、请求间隔、重试次数、7-Zip 路径、解压后删除原档等。修改后重新打开窗口。原命令行入口 `.\.venv\Scripts\python.exe main.py` 保留。

请勿同时启动多个 GUI 或同时运行 GUI 与 CLI：它们使用同一组配置和输出文件。并行数量不会突破 Nexus 账号本身的限速。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试在临时目录内运行，覆盖配置保留、输入校验、真实本地 HTTP 下载、取消登录和窗口启动/停止/重复运行。窗口测试需要可用的 Tk 显示环境。它们不会读取真实 Nexus 凭据，也不访问 Nexus；真实登录和站点下载兼容性仍需使用者验证。


## 构建 Windows EXE

在已执行 Setup-GUI.cmd 的 Windows x64 环境运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build-release.ps1 -Version 0.1.0
```

脚本运行测试，再用 PyInstaller 分别打包窗口与后台，输出 `release/` 下的便携 ZIP 和 SHA-256 校验文件。打包使用明确的文件清单，不包含 Cookie、会话、下载或本机配置。
