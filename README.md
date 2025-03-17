# 音乐一直放！

一个自动监控和控制音乐播放的小工具，确保在没有其他音频播放时，LX Music会自动播放音乐。

## 功能特点

- 自动检测其他程序是否在播放音频
- 当没有其他音频播放时，自动启动LX Music播放音乐
- 当检测到其他程序播放音频时，自动暂停LX Music
- 美观的现代化界面，支持亮色/暗色主题切换
- 无边框设计，支持拖拽和最小化

## 使用方法

1. 确保已安装LX Music Desktop
2. 运行本程序
3. 点击"开始监控"按钮（或默认自动开始监控）
4. 程序会在后台自动管理音乐播放状态

## 依赖库

- PyQt6
- pycaw
- pyautogui
- psutil
- pywin32

## 安装依赖

```bash
pip install PyQt6 pycaw pyautogui psutil pywin32

git remote add origin https://github.com/wuqie-xuanzhao/MusicAlwaysPlay.git
git branch -M main
git push -u origin main