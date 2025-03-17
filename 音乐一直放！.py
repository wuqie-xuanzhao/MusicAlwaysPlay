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
                            QCheckBox, QFrame, QLineEdit)  # 添加QLineEdit导入
from PyQt6.QtCore import QTimer, Qt, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor, QPainter, QPen, QCursor

# 配置部分
# 修改为可配置的音乐播放器设置
DEFAULT_MUSIC_PLAYER = 'lx-music-desktop.exe'  # 默认音乐播放器进程名
DEFAULT_HOTKEY = ['ctrl', 'alt', 'p']  # 默认播放/暂停快捷键
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
        
        # 获取父窗口的主题模式
        is_light_mode = False
        parent = self.parent()
        while parent:
            if hasattr(parent, "is_light_mode"):
                is_light_mode = parent.is_light_mode
                break
            parent = parent.parent()
        
        # 设置画笔颜色
        if self.underMouse():
            # 悬停时使用白色
            pen_color = QColor("#FFFFFF")
        else:
            if is_light_mode:
                # 光模式下使用深色图标
                pen_color = QColor("#333333")
            else:
                # 暗模式下使用浅色图标
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
            # 在加载图标的地方添加以下代码
            def resource_path(relative_path):
                """获取资源的绝对路径，兼容开发环境和PyInstaller打包后的环境"""
                try:
                    # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
                    base_path = sys._MEIPASS
                except Exception:
                    base_path = os.path.abspath(".")
                
                return os.path.join(base_path, relative_path)
            
            # 然后将所有加载图标的代码从：
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
            
            # 修改为：
            icon_path = resource_path("icon.png")
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
        app_font.setPixelSize(15)  # 将字体大小从13增加到15
        app_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)  # 增强字体提示
        QApplication.setFont(app_font)
        
        if self.is_light_mode:
            # 白天模式
            self.setStyleSheet(f"""
                * {{
                    font-family: {font_family};
                    font-size: 15px;  /* 将字体大小从13px增加到15px */
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
                    font-size: 16px;  /* 将标题字体从14px增加到16px */
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
                    font-size: 14px;  /* 将字体大小从12px增加到14px */
                    line-height: 1.5;
                }}
                QScrollBar:vertical {{
                    background: #F0F0F0;
                    width: 12px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: #CCCCCC;
                    min-height: 20px;
                    border-radius: 6px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: #AAAAAA;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: none;
                }}
                QScrollBar:horizontal {{
                    background: #F0F0F0;
                    height: 12px;
                    margin: 0px;
                }}
                QScrollBar::handle:horizontal {{
                    background: #CCCCCC;
                    min-width: 20px;
                    border-radius: 6px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background: #AAAAAA;
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    width: 0px;
                }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                    background: none;
                }}
                QLineEdit {{
                    background-color: #FFFFFF;
                    color: #333333;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                    padding: 4px 8px;
                    selection-background-color: #0078D7;
                    selection-color: white;
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
                    font-size: 15px;  /* 将字体大小从13px增加到15px */
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
                    font-size: 16px;  /* 将标题字体从14px增加到16px */
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
                    font-family: "Consolas", "Microsoft YaHei UI", monospace;
                    font-size: 14px;  /* 将字体大小从12px增加到14px */
                    line-height: 1.5;
                }}
                QScrollBar:vertical {{
                    background: #2A2A2A;
                    width: 12px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: #555555;
                    min-height: 20px;
                    border-radius: 6px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: #666666;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: none;
                }}
                QScrollBar:horizontal {{
                    background: #2A2A2A;
                    height: 12px;
                    margin: 0px;
                }}
                QScrollBar::handle:horizontal {{
                    background: #555555;
                    min-width: 20px;
                    border-radius: 6px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background: #666666;
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    width: 0px;
                }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                    background: none;
                }}
                QLineEdit {{
                    background-color: #252526;
                    color: #FFFFFF;
                    border: 1px solid #3F3F46;
                    border-radius: 4px;
                    padding: 4px 8px;
                    selection-background-color: #0078D7;
                    selection-color: white;
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
        
        # 强制更新标题栏按钮
        if hasattr(self, 'theme_button'):
            self.theme_button.update()
        if hasattr(self, 'minimize_button'):
            self.minimize_button.update()
        if hasattr(self, 'close_button'):
            self.close_button.update()
    
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
        
        # 主题切换按钮 - 使用相同的hover_color
        self.theme_button = TitleBarButton(self, hover_color="#0078D7")
        self.theme_button.setObjectName("themeButton")
        self.theme_button.setToolTip("切换主题")
        self.theme_button.clicked.connect(self.toggle_theme)
        
        # 最小化按钮
        self.minimize_button = TitleBarButton(self, hover_color="#0078D7")
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

# 将AudioMonitorApp类移到全局作用域，并删除重复的main函数定义

# 在ModernWindow类之后添加AudioMonitorApp类
class AudioMonitorApp(ModernWindow):
    def __init__(self):
        super().__init__()
        # 修改软件标题为"音乐一直放！"
        self.setWindowTitle("音乐一直放！")
        self.setGeometry(100, 100, 600, 450)  # 增加高度以容纳新控件
        
        # 状态变量
        self.last_other_playing = False
        self.last_lx_playing = False
        self.last_action = None
        self.consecutive_attempts = 0
        self.last_action_time = 0
        self.running = False
        self.no_volume_count = 0
        
        # 音乐播放器设置
        self.music_player = DEFAULT_MUSIC_PLAYER
        self.music_hotkey = DEFAULT_HOTKEY
        
        # 创建定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_audio_status)
        
        # 创建界面
        self.init_ui()
    
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
        
        # 添加GitHub链接 - 增加按钮宽度
        github_button = QPushButton("GitHub")
        github_button.setFixedWidth(100)  # 从80增加到100
        github_button.setToolTip("访问GitHub仓库")
        github_button.clicked.connect(self.open_github)
        status_layout.addWidget(github_button)
        
        layout.addWidget(self.status_frame)
        
        # 添加音乐播放器设置区域
        settings_frame = QFrame()
        settings_frame.setObjectName("settingsFrame")
        settings_layout = QVBoxLayout(settings_frame)
        
        # 音乐播放器选择
        player_layout = QHBoxLayout()
        player_label = QLabel("音乐播放器进程名:")
        self.player_input = QLineEdit(self.music_player)
        self.player_input.setToolTip("输入音乐播放器的进程名称，例如：lx-music-desktop.exe")
        self.player_input.textChanged.connect(self.update_music_player)
        player_layout.addWidget(player_label)
        player_layout.addWidget(self.player_input)
        settings_layout.addLayout(player_layout)
        
        # 快捷键设置
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("播放/暂停快捷键:")
        self.hotkey_input = QLineEdit('+'.join(self.music_hotkey))
        self.hotkey_input.setToolTip("输入控制音乐播放/暂停的快捷键，例如：ctrl+alt+p")
        self.hotkey_input.textChanged.connect(self.update_hotkey)
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_input)
        settings_layout.addLayout(hotkey_layout)
        
        layout.addWidget(settings_frame)
        
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
        self.log(f"当前音乐播放器: {self.music_player}")
        self.log(f"当前快捷键: {'+'.join(self.music_hotkey)}")
        
        # 如果选中了自动启动，则启动监控
        if self.auto_start_checkbox.isChecked():
            self.toggle_monitoring()
    
    def update_music_player(self, text):
        """更新音乐播放器设置"""
        self.music_player = text.strip()
        self.log(f"音乐播放器已更新为: {self.music_player}")
    
    def update_hotkey(self, text):
        """更新快捷键设置"""
        keys = [k.strip().lower() for k in text.split('+') if k.strip()]
        if keys:
            self.music_hotkey = keys
            self.log(f"快捷键已更新为: {'+'.join(self.music_hotkey)}")
    
    def log(self, message):
        """添加日志消息"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text.append(f"[{timestamp}] {message}")
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def toggle_monitoring(self):
        """切换监控状态"""
        if self.running:
            self.timer.stop()
            self.running = False
            self.start_button.setText("开始监控")
            self.status_label.setText("状态: 未运行")
            self.status_icon.setStyleSheet("color: #888888; font-size: 16px;")
            self.log("监控已停止")
        else:
            self.timer.start(3000)  # 每3秒检查一次
            self.running = True
            self.start_button.setText("停止监控")
            self.status_label.setText("状态: 运行中")
            self.status_icon.setStyleSheet("color: #4CAF50; font-size: 16px;")
            self.log("监控已启动")
    
    def 检测LX_Music是否在播放音频(self):
        """检测音乐播放器是否在播放音频，通过窗口标题和音量判断"""
        try:
            # 首先检查音乐播放器进程是否存在
            music_player_running = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == self.music_player.lower():
                    music_player_running = True
                    break
            
            if not music_player_running:
                self.log(f"音乐播放器进程 {self.music_player} 未运行")
                return False
            
            # 查找音乐播放器窗口
            music_player_title = ""
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        process = psutil.Process(pid)
                        if process.name().lower() == self.music_player.lower():
                            title = win32gui.GetWindowText(hwnd)
                            if title:
                                extra[0] = title
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                return True
            
            window_title = [""]  # 使用列表作为可变对象传递结果
            win32gui.EnumWindows(callback, window_title)
            music_player_title = window_title[0]
            
            self.log(f"音乐播放器窗口标题: '{music_player_title}'")
            
            # 使用音量检测作为主要判断方法
            peak_value = 0.0
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.Process.name().lower() == self.music_player.lower():
                    meter = session._ctl.QueryInterface(IAudioMeterInformation)
                    peak_value = meter.GetPeakValue()
                    self.log(f"音乐播放器音量峰值: {peak_value}")
                    break
            
            # 根据音量判断播放状态
            # 如果音量大于阈值，则认为正在播放
            if peak_value > PEAK_THRESHOLD:
                return True
            # 如果音量极低（接近0但不是0），则认为是暂停状态
            elif peak_value > 0 and peak_value < VERY_LOW_THRESHOLD:
                self.log("音乐播放器已暂停（极低音量）")
                return False
            
            # 如果音量检测不确定，则使用窗口标题辅助判断
            if "- 暂停中" in music_player_title or "- paused" in music_player_title.lower():
                return False
            
            # 如果窗口标题包含歌曲名，且没有明确的暂停标识，则可能在播放
            is_playing_by_title = bool(music_player_title and not music_player_title.endswith(self.music_player.replace(".exe", "")))
            
            # 如果标题判断为播放中，但音量为0，则需要进一步确认
            if is_playing_by_title and peak_value == 0:
                self.no_volume_count += 1
                if self.no_volume_count > 2:  # 连续3次检测
                    self.log("音乐播放器可能已暂停（无音量）")
                    return False
            else:
                self.no_volume_count = 0
            
            return is_playing_by_title
            
        except Exception as e:
            self.log(f"检测音乐播放器状态时出错: {e}")
            return False
    
    def 控制LX_Music(self, action):
        """控制音乐播放器的播放状态"""
        if action == 'play' or action == 'pause':
            self.log(f"发送快捷键 {'+'.join(self.music_hotkey)} 到音乐播放器 ({action})")
            pyautogui.hotkey(*self.music_hotkey)
            # 等待一小段时间让操作生效
            time.sleep(1)
    
    def 检测其他程序是否在播放音频(self):
        """检测其他程序是否在播放音频"""
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if not session.Process:
                continue
            process_name = session.Process.name().lower()
            if process_name == self.music_player.lower():
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
            
            self.log(f"调试信息 - 其他程序播放状态: {other_playing}, 音乐播放器播放状态: {lx_playing}")
            
            # 添加操作冷却时间，避免频繁切换
            cooldown_passed = (current_time - self.last_action_time) > 5  # 5秒冷却时间
            
            # 情况1: 其他程序正在播放，确保LX Music暂停
            if other_playing:
                if lx_playing and cooldown_passed:
                    self.log("检测到其他程序正在播放，暂停音乐播放器")
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
                        self.log(f"没有检测到任何音频播放，启动音乐播放器 (尝试 {self.consecutive_attempts}/3)")
                        self.控制LX_Music('play')
                        self.last_action = 'play'
                        self.last_action_time = current_time
                        time.sleep(2)  # 给音乐播放器一些启动时间
                    else:
                        self.log("多次尝试启动音乐播放器未成功，暂停尝试")
                        time.sleep(15)  # 等待更长时间再尝试
                        self.consecutive_attempts = 0
                else:
                    self.consecutive_attempts = 0  # 音乐播放器已经在播放，重置计数
            
            # 更新上一次的状态
            self.last_other_playing = other_playing
            self.last_lx_playing = lx_playing
            
        except Exception as e:
            self.log(f"发生错误: {e}")
    
    def open_github(self):
        """打开GitHub仓库页面"""
        import webbrowser
        webbrowser.open("https://github.com/wuqie-xuanzhao/MusicAlwaysPlay")
        self.log("正在打开GitHub仓库页面...")

# 删除类内部的main函数定义，将其移到类外部
# 在AudioMonitorApp类定义之后，添加以下代码
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
    
    # 删除了设置高DPI属性的代码，避免错误
    
    # 设置应用程序名称
    app.setApplicationName("音乐一直放！")
    window = AudioMonitorApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()