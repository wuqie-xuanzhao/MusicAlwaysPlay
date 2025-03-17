from PIL import Image
import os

# 检查是否存在PNG图标
png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

if os.path.exists(png_path):
    try:
        # 打开PNG图像
        img = Image.open(png_path)
        
        # 转换为ICO格式并保存
        img.save(ico_path, format='ICO')
        
        print(f"图标已成功转换为ICO格式: {ico_path}")
    except Exception as e:
        print(f"转换图标时出错: {e}")
else:
    print(f"PNG图标文件不存在: {png_path}")