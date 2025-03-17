import os
import sys
import shutil
import subprocess

# 确保当前目录是项目目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 应用程序名称
app_name = "音乐一直放！"

# 清理之前的构建文件
if os.path.exists("dist"):
    shutil.rmtree("dist")
if os.path.exists("build"):
    shutil.rmtree("build")
if os.path.exists(f"{app_name}.spec"):
    os.remove(f"{app_name}.spec")

# 图标文件路径
icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
if not os.path.exists(icon_path):
    print("警告: 图标文件不存在，将使用默认图标")
    icon_path = None

# 首先卸载不兼容的pathlib包
try:
    print("尝试卸载不兼容的pathlib包...")
    subprocess.call([sys.executable, "-m", "pip", "uninstall", "-y", "pathlib"])
    print("pathlib包已卸载")
except Exception as e:
    print(f"卸载pathlib时出错: {e}")

# 构建命令
cmd = [
    "pyinstaller",
    "--name", app_name,
    "--windowed",  # 使用GUI模式，不显示控制台
    "--noconfirm",  # 不询问确认
    "--clean",  # 清理临时文件
    "--onefile",  # 打包成单个文件
    "--log-level", "INFO",
]

# 添加图标文件作为数据文件
if os.path.exists("icon.png"):
    # 在Windows上，分隔符需要使用分号
    cmd.extend(["--add-data", f"icon.png{os.pathsep}."])

# 添加图标
if icon_path:
    cmd.extend(["--icon", icon_path])

# 添加主程序文件
cmd.append("音乐一直放！.py")

# 执行打包命令
print("开始打包...")
result = subprocess.call(cmd)

# 检查打包是否成功
if result == 0:
    print(f"打包完成！可执行文件位于: {os.path.join('dist', app_name + '.exe')}")
else:
    print("打包失败，请检查错误信息")