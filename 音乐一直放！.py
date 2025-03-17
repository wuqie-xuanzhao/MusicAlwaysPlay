from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
import comtypes
import time
import pyautogui
import psutil
import win32gui
import win32process
import sys
import os
import math  # 添加math模块导入
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, 
                            QCheckBox, QFrame)
from PyQt6.QtCore import QTimer, Qt, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor, QPainter, QPen, QCursor

# 配置部分
MUSIC_PLAYER_PROCESSES = ['lx-music-desktop.exe']  # 需要排除的音乐播放器进程名
PEAK_THRESHOLD = 0.01  # 声音触发阈值（0.0-1.0）
VERY_LOW_THRESHOLD = 1e-8  # 极低音量阈值，用于检测暂停状态

# 自定义标题栏按钮
class TitleBarButton(QPushButton):
    def __init__(self, parent=None, icon_color="#FFFFFF", hover_color="#E81123"):
        super().__init__(parent)
        self.icon_color = icon_color
        self.hover_color = hover_color
        self.setFixedSize(46, 32)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 设置画笔颜色
        if self.underMouse():
            pen_color = QColor("#FFFFFF")
        else:
            pen_color = QColor(self.icon_color)
        
        pen = QPen(pen_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # 绘制图标
        rect = self.rect()
        center_x = rect.width() // 2
        center_y = rect.height() // 2

        # 这里可以根据按钮类型绘制不同的图标
        if self.objectName() == "closeButton":
            # 绘制X形状
            painter.drawLine(center_x - 8, center_y - 8, center_x + 8, center_y + 8)
            painter.drawLine(center_x + 8, center_y - 8, center_x - 8, center_y + 8)
        elif self.objectName() == "minimizeButton":
            # 绘制-形状
            painter.drawLine(center_x - 8, center_y, center_x + 8, center_y)
        elif self.objectName() == "themeButton":
            # 绘制主题切换图标（太阳/月亮）
            is_light_mode = False
            if self.parent():
                is_light_mode = getattr(self.parent(), "is_light_mode", False)
            
            if is_light_mode:
                # 绘制月亮图标
                painter.drawEllipse(center_x - 7, center_y - 7, 14, 14)
                # 绘制月亮阴影
                painter.setBrush(QColor(self.parent().palette().color(self.parent().backgroundRole())))
                painter.drawEllipse(center_x - 3, center_y - 9, 12, 12)
            else:
                # 绘制太阳图标
                painter.drawEllipse(center_x - 5, center_y - 5, 10, 10)
                # 绘制太阳光芒
                for i in range(8):
                    angle = i * 45
                    rad = angle * 3.14159 / 180
                    x1 = center_x + 7 * round(math.cos(rad))
                    y1 = center_y + 7 * round(math.sin(rad))
                    x2 = center_x + 10 * round(math.cos(rad))
                    y2 = center_y + 10 * round(math.sin(rad))
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
# 自定义无边框窗口
class ModernWindow(QMainWindow):
    # 在ModernWindow类的__init__方法中
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 主题模式（默认为暗色模式）
        self.is_light_mode = False
        
        # 修改图标加载方式
        try:
            # 尝试直接从当前文件目录加载图标
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
            if os.path.exists(icon_path):
                app_icon = QIcon(icon_path)
                self.setWindowIcon(app_icon)
                QApplication.setWindowIcon(app_icon)  # 设置应用程序图标
            else:
                print(f"图标文件不存在: {icon_path}")
        except Exception as e:
            print(f"加载图标时出错: {e}")
        
        # 拖动相关变量
        self._drag_position = None
        self._is_dragging = False
        
        # 创建主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建标题栏
        self.create_title_bar()
        
        # 创建内容区域
        self.content_frame = QFrame()
        self.content_frame.setObjectName("contentFrame")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.addWidget(self.content_frame)
        
        # 设置中央窗口部件
        central_widget = QWidget()
        central_widget.setObjectName("windowFrame")
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)
        
        # 应用主题
        self.apply_theme()
    
    def apply_theme(self):
        """应用当前主题样式"""
        # 设置字体 - 优化字体渲染设置
        font_family = "PingFang SC, Microsoft YaHei UI, Microsoft YaHei, SimHei, sans-serif"
        
        # 创建应用程序字体
        app_font = QFont()
        app_font.setFamily(font_family.split(',')[0].strip())  # 使用第一个字体
        app_font.setPixelSize(13)  # 使用像素大小而不是点大小
        app_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)  # 增强字体提示
        QApplication.setFont(app_font)
        
        if self.is_light_mode:
            # 白天模式
            self.setStyleSheet(f"""
                * {{
                    font-family: {font_family};
                    font-size: 13px;
                    letter-spacing: 0.3px;  /* 增加字母间距 */
                }}
                #windowFrame {{
                    background-color: #F5F5F5;
                    border-radius: 8px;
                }}
                #titleBar {{
                    background-color: #E0E0E0;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }}
                #titleLabel {{
                    color: #333333;
                    font-size: 14px;
                    font-weight: bold;
                }}
                #contentFrame {{
                    background-color: #F5F5F5;
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                }}
                #statusFrame {{
                    background-color: #E8E8E8;
                    border-radius: 4px;
                    padding: 5px;
                }}
                QLabel {{
                    color: #333333;
                }}
                QTextEdit {{
                    background-color: #FFFFFF;
                    color: #333333;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                    font-family: "Consolas", "Microsoft YaHei UI", monospace;
                    font-size: 12px;
                    line-height: 1.5;
                }}
                QPushButton {{
                    background-color: #0078D7;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #1C97EA;
                }}
                QPushButton:pressed {{
                    background-color: #0063B1;
                }}
                QCheckBox {{
                    color: #333333;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #0078D7;
                    border: 1px solid #0078D7;
                }}
            """)
            
            # 更新状态图标颜色
            if hasattr(self, 'status_icon'):
                if self.running:
                    self.status_icon.setStyleSheet("color: #4CAF50; font-size: 16px;")
                else:
                    self.status_icon.setStyleSheet("color: #888888; font-size: 16px;")
        else:
            # 暗色模式
            self.setStyleSheet(f"""
                * {{
                    font-family: {font_family};
                    font-size: 13px;
                    letter-spacing: 0.3px;  /* 增加字母间距 */
                }}
                #windowFrame {{
                    background-color: #2D2D30;
                    border-radius: 8px;
                }}
                #titleBar {{
                    background-color: #1E1E1E;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }}
                #titleLabel {{
                    color: #FFFFFF;
                    font-size: 14px;
                    font-weight: bold;
                }}
                #contentFrame {{
                    background-color: #2D2D30;
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                }}
                #statusFrame {{
                    background-color: #333337;
                    border-radius: 4px;
                    padding: 5px;
                }}
                QLabel {{
                    color: #FFFFFF;
                }}
                QTextEdit {{
                    background-color: #252526;
                    color: #FFFFFF;
                    border: 1px solid #3F3F46;
                    border-radius: 4px;
                }}
                QPushButton {{
                    background-color: #0078D7;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #1C97EA;
                }}
                QPushButton:pressed {{
                    background-color: #0063B1;
                }}
                QCheckBox {{
                    color: #FFFFFF;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 1px solid #3F3F46;
                    border-radius: 3px;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #0078D7;
                    border: 1px solid #0078D7;
                }}
            """)
            
            # 更新状态图标颜色
            if hasattr(self, 'status_icon'):
                if self.running:
                    self.status_icon.setStyleSheet("color: #4CAF50; font-size: 16px;")
                else:
                    self.status_icon.setStyleSheet("color: #888888; font-size: 16px;")
    
    def toggle_theme(self):
        """切换主题模式"""
        self.is_light_mode = not self.is_light_mode
        self.apply_theme()
    
    def create_title_bar(self):
        # 创建标题栏
        self.title_bar = QFrame()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(40)
        self.title_bar.mousePressEvent = self.title_bar_mouse_press
        self.title_bar.mouseMoveEvent = self.title_bar_mouse_move
        self.title_bar.mouseReleaseEvent = self.title_bar_mouse_release
        self.title_bar.mouseDoubleClickEvent = self.title_bar_double_click
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        title_layout.setSpacing(0)
        
        # 图标
        self.icon_label = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        self.icon_label.setFixedSize(30, 30)
        title_layout.addWidget(self.icon_label)
        
        # 标题
        self.title_label = QLabel("音乐一直放！")
        self.title_label.setObjectName("titleLabel")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        # 主题切换按钮
        self.theme_button = TitleBarButton(self, hover_color="#0078D7")
        self.theme_button.setObjectName("themeButton")
        self.theme_button.setToolTip("切换主题")
        self.theme_button.clicked.connect(self.toggle_theme)
        
        # 最小化按钮
        self.minimize_button = TitleBarButton(self)
        self.minimize_button.setObjectName("minimizeButton")
        self.minimize_button.setToolTip("最小化")
        self.minimize_button.clicked.connect(self.showMinimized)
        
        # 关闭按钮
        self.close_button = TitleBarButton(self, hover_color="#E81123")
        self.close_button.setObjectName("closeButton")
        self.close_button.setToolTip("关闭")
        self.close_button.clicked.connect(self.close)
        
        # 添加按钮到标题栏
        title_layout.addWidget(self.theme_button)
        title_layout.addWidget(self.minimize_button)
        title_layout.addWidget(self.close_button)
        
        # 添加标题栏到主布局
        self.main_layout.addWidget(self.title_bar)
    
    def title_bar_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = True
            event.accept()
    
    def title_bar_mouse_move(self, event):
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
    
    def title_bar_mouse_release(self, event):
        self._is_dragging = False
    
    def title_bar_double_click(self, event):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

class AudioMonitorApp(ModernWindow):
    def __init__(self):
        super().__init__()
        # 修改软件标题为"音乐一直放！"
        self.setWindowTitle("音乐一直放！")
        self.setGeometry(100, 100, 600, 400)
        
        # 状态变量
        self.last_other_playing = False
        self.last_lx_playing = False
        self.last_action = None
        self.consecutive_attempts = 0
        self.last_action_time = 0
        self.running = False
        self.no_volume_count = 0
        
        # 创建定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_audio_status)
        
        # 创建界面
        self.init_ui()
        
    # 在AudioMonitorApp类的init_ui方法中添加GitHub链接按钮
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 状态显示
        self.status_frame = QFrame()
        self.status_frame.setObjectName("statusFrame")
        status_layout = QHBoxLayout(self.status_frame)
        
        status_icon = QLabel("●")
        status_icon.setStyleSheet("color: #888888; font-size: 16px;")
        status_icon.setFixedWidth(20)
        self.status_icon = status_icon
        
        self.status_label = QLabel("状态: 未运行")
        
        status_layout.addWidget(status_icon)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        # 添加GitHub链接
        github_button = QPushButton("GitHub")
        github_button.setFixedWidth(80)
        github_button.setToolTip("访问GitHub仓库")
        github_button.clicked.connect(self.open_github)
        status_layout.addWidget(github_button)
        
        layout.addWidget(self.status_frame)
        
        # 日志显示
        log_label = QLabel("运行日志")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        layout.addWidget(self.log_text)
        
        # 自动启动选项
        self.auto_start_checkbox = QCheckBox("程序启动时自动开始监控")
        self.auto_start_checkbox.setChecked(True)
        layout.addWidget(self.auto_start_checkbox)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_button = QPushButton("开始监控")
        self.start_button.setFixedWidth(120)
        self.start_button.clicked.connect(self.toggle_monitoring)
        button_layout.addWidget(self.start_button)
        
        layout.addLayout(button_layout)
        
        # 设置内容布局
        self.content_layout.addLayout(layout)
        
        # 添加日志
        self.log("音频监控系统已启动")
        
        # 如果选中了自动启动，则启动监控
        if self.auto_start_checkbox.isChecked():
            self.toggle_monitoring()
    
    def log(self, message):
        """添加日志到日志窗口"""
        self.log_text.append(f"[{time.strftime('%H:%M:%S')}] {message}")
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def toggle_monitoring(self):
        """切换监控状态"""
        if not self.running:
            self.running = True
            self.start_button.setText("停止监控")
            self.status_label.setText("状态: 正在监控")
            self.status_icon.setStyleSheet("color: #4CAF50; font-size: 16px;")  # 绿色
            self.log("开始音频监控")
            self.timer.start(2000)  # 每2秒检查一次
        else:
            self.running = False
            self.start_button.setText("开始监控")
            self.status_label.setText("状态: 已停止")
            self.status_icon.setStyleSheet("color: #888888; font-size: 16px;")  # 灰色
            self.log("停止音频监控")
            self.timer.stop()
    
    def 检测LX_Music是否在播放音频(self):
        """检测LX_Music是否在播放音频，通过窗口标题和音量判断"""
        try:
            # 首先检查LX Music进程是否存在
            lx_music_running = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == 'lx-music-desktop.exe':
                    lx_music_running = True
                    break
            
            if not lx_music_running:
                self.log("LX Music进程未运行")
                return False
            
            # 查找LX Music窗口
            lx_music_title = ""
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        process = psutil.Process(pid)
                        if process.name().lower() == 'lx-music-desktop.exe':
                            title = win32gui.GetWindowText(hwnd)
                            if title:
                                extra[0] = title
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                return True
            
            window_title = [""]  # 使用列表作为可变对象传递结果
            win32gui.EnumWindows(callback, window_title)
            lx_music_title = window_title[0]
            
            self.log(f"LX Music窗口标题: '{lx_music_title}'")
            
            # 使用音量检测作为主要判断方法
            peak_value = 0.0
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.Process.name().lower() == 'lx-music-desktop.exe':
                    meter = session._ctl.QueryInterface(IAudioMeterInformation)
                    peak_value = meter.GetPeakValue()
                    self.log(f"LX Music音量峰值: {peak_value}")
                    break
            
            # 根据音量判断播放状态
            # 如果音量大于阈值，则认为正在播放
            if peak_value > PEAK_THRESHOLD:
                return True
            # 如果音量极低（接近0但不是0），则认为是暂停状态
            elif peak_value > 0 and peak_value < VERY_LOW_THRESHOLD:
                self.log("LX Music已暂停（极低音量）")
                return False
            
            # 如果音量检测不确定，则使用窗口标题辅助判断
            if "- 暂停中" in lx_music_title or "- paused" in lx_music_title.lower():
                return False
            
            # 如果窗口标题包含歌曲名（不只是"LX Music"），且没有明确的暂停标识，则可能在播放
            is_playing_by_title = bool(lx_music_title and not lx_music_title.endswith("LX Music"))
            
            # 如果标题判断为播放中，但音量为0，则需要进一步确认
            if is_playing_by_title and peak_value == 0:
                self.no_volume_count += 1
                if self.no_volume_count > 2:  # 连续3次检测
                    self.log("LX Music可能已暂停（无音量）")
                    return False
            else:
                self.no_volume_count = 0
            
            return is_playing_by_title
            
        except Exception as e:
            self.log(f"检测LX Music状态时出错: {e}")
            return False
    
    def 控制LX_Music(self, action):
        """控制LX_Music的播放状态"""
        if action == 'play' or action == 'pause':
            self.log(f"发送快捷键 Ctrl+Alt+P 到LX Music ({action})")
            pyautogui.hotkey('ctrl', 'alt', 'p')
            # 等待一小段时间让操作生效
            time.sleep(1)
    
    def 检测其他程序是否在播放音频(self):
        """检测其他程序是否在播放音频"""
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if not session.Process:
                continue
            process_name = session.Process.name().lower()
            if process_name in MUSIC_PLAYER_PROCESSES:
                continue
            meter = session._ctl.QueryInterface(IAudioMeterInformation)
            if meter.GetPeakValue() > PEAK_THRESHOLD:
                return True
        return False
    
    def check_audio_status(self):
        """检查音频状态并执行相应操作"""
        try:
            current_time = time.time()
            other_playing = self.检测其他程序是否在播放音频()
            lx_playing = self.检测LX_Music是否在播放音频()
            
            self.log(f"调试信息 - 其他程序播放状态: {other_playing}, LX Music播放状态: {lx_playing}")
            
            # 添加操作冷却时间，避免频繁切换
            cooldown_passed = (current_time - self.last_action_time) > 5  # 5秒冷却时间
            
            # 情况1: 其他程序正在播放，确保LX Music暂停
            if other_playing:
                if lx_playing and cooldown_passed:
                    self.log("检测到其他程序正在播放，暂停LX Music")
                    self.控制LX_Music('pause')
                    self.last_action = 'pause'
                    self.last_action_time = current_time
                self.consecutive_attempts = 0  # 重置连续尝试计数
            # 情况2: 其他程序不在播放，确保LX Music在播放
            elif not other_playing and cooldown_passed:
                # 如果LX Music没有播放，启动它
                if not lx_playing:
                    # 添加防止循环触发的逻辑
                    self.consecutive_attempts += 1
                    if self.consecutive_attempts <= 3:  # 最多尝试3次
                        self.log(f"没有检测到任何音频播放，启动LX Music (尝试 {self.consecutive_attempts}/3)")
                        self.控制LX_Music('play')
                        self.last_action = 'play'
                        self.last_action_time = current_time
                        time.sleep(2)  # 给LX Music一些启动时间
                    else:
                        self.log("多次尝试启动LX Music未成功，暂停尝试")
                        time.sleep(15)  # 等待更长时间再尝试
                        self.consecutive_attempts = 0
                else:
                    self.consecutive_attempts = 0  # LX Music已经在播放，重置计数
            
            # 更新上一次的状态
            self.last_other_playing = other_playing
            self.last_lx_playing = lx_playing
            
        except Exception as e:
            self.log(f"发生错误: {e}")

def main():
    # 使用Windows API直接设置DPI感知模式
    try:
        import ctypes
        # 使用系统DPI感知 - 允许每个显示器使用不同的缩放
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 2 = 每显示器DPI感知
    except Exception as e:
        print(f"设置DPI感知模式失败: {e}")
    
    # 启用高DPI缩放
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    # 移除固定DPI值设置
    if "QT_FONT_DPI" in os.environ:
        del os.environ["QT_FONT_DPI"]
    
    app = QApplication(sys.argv)
    
    # 在PyQt6中正确设置高DPI属性
    try:
        # 使用正确的枚举值
        app.setAttribute(Qt.ApplicationAttribute.UseHighDpiPixmaps)
        # 设置DPI缩放策略
        if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
            app.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception as e:
        print(f"设置高DPI属性失败: {e}")
    
    # 设置应用程序名称
    app.setApplicationName("音乐一直放！")
    window = AudioMonitorApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

# 添加打开GitHub的方法
def open_github(self):
    """打开GitHub仓库页面"""
    import webbrowser
    webbrowser.open("https://github.com/你的用户名/MusicAlwaysPlay")
    self.log("正在打开GitHub仓库页面...")