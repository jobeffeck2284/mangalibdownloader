import os
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QWidget, QComboBox, QHBoxLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor, QTextCharFormat, QPalette
from PIL import Image

# Стили для тем
LIGHT_THEME = """
    QWidget {
        background-color: #FFFFFF;
        color: #333333;
        font-family: 'Segoe UI';
    }
    QPushButton {
        background-color: #FF6B35;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #FF7F50;
    }
    QPushButton:disabled {
        background-color: #CCCCCC;
    }
    QLineEdit, QTextEdit {
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        padding: 6px;
        font-size: 14px;
    }
    QComboBox {
        padding: 4px;
        border: 1px solid #CCCCCC;
        border-radius: 4px;
    }
"""

DARK_THEME = """
    QWidget {
        background-color: #2D2D2D;
        color: #CCCCCC;
        font-family: 'Segoe UI';
    }
    QPushButton {
        background-color: #FF6B35;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #FF7F50;
    }
    QPushButton:disabled {
        background-color: #555555;
    }
    QLineEdit, QTextEdit {
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 6px;
        background-color: #404040;
        color: #CCCCCC;
        font-size: 14px;
    }
    QComboBox {
        padding: 4px;
        border: 1px solid #555555;
        border-radius: 4px;
        background-color: #404040;
        color: #CCCCCC;
    }
"""


def get_manga_pages(slug_url, volume_number, chapter_number):
    base_url = "https://api.lib.social/api/manga"
    endpoint = f"{base_url}/{slug_url}/chapter"
    params = {
        "number": chapter_number,
        "volume": volume_number
    }

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pages = data.get("data", {}).get("pages", [])
            return [
                f"https://img33.imgslib.link{page['url']}"
                if page["url"].startswith("//manga/") else page["url"]
                for page in pages
            ]
        return []
    except Exception as e:
        return []


def sanitize_folder_name(name):
    return "".join(c if c.isalnum() else "_" for c in name)


class DownloadThread(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(str)

    def __init__(self, slug_url, volume_number, chapter_number, parent=None):
        super().__init__(parent)
        self.slug_url = slug_url
        self.volume_number = volume_number
        self.chapter_number = chapter_number

    def run(self):
        try:
            self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Начало загрузки...", "info")

            folder_name = sanitize_folder_name(self.slug_url.split("--", 1)[-1])
            volume_folder = f"Volume_{self.volume_number}"
            chapter_folder = f"Chapter_{self.chapter_number}"

            save_dir = os.path.join(os.path.dirname(__file__), "manga", folder_name, volume_folder, chapter_folder)
            os.makedirs(save_dir, exist_ok=True)

            self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Поиск страниц...", "info")
            page_urls = get_manga_pages(self.slug_url, self.volume_number, self.chapter_number)

            if not page_urls:
                self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Страницы не найдены!", "error")
                self.finished_signal.emit("")
                return

            image_paths = []
            for i, url in enumerate(page_urls, start=1):
                try:
                    response = requests.get(url, stream=True, timeout=15)
                    if response.status_code == 200:
                        image_path = os.path.join(save_dir, f"{i:03}.jpg")
                        with open(image_path, "wb") as img_file:
                            for chunk in response.iter_content(2048):
                                img_file.write(chunk)
                        image_paths.append(image_path)
                        self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Страница {i} сохранена",
                                             "success")
                    else:
                        self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Ошибка загрузки: {url}", "error")
                except Exception as e:
                    self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Ошибка: {str(e)}", "error")

            if image_paths:
                pdf_path = os.path.join(save_dir, f"Volume_{self.volume_number}_Chapter_{self.chapter_number}.pdf")
                self.create_pdf_with_pillow(image_paths, pdf_path)
                self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] PDF создан: {pdf_path}", "success")

            self.finished_signal.emit(save_dir)

        except Exception as e:
            self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Критическая ошибка: {str(e)}", "error")
            self.finished_signal.emit("")

    def create_pdf_with_pillow(self, image_paths, output_path):
        try:
            images = [Image.open(img).convert("RGB") for img in image_paths]
            if images:
                images[0].save(output_path, save_all=True, append_images=images[1:])
        except Exception as e:
            self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Ошибка создания PDF: {str(e)}", "error")


class MangaDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_theme = "light"
        self.last_save_dir = ""
        self.init_ui()
        self.apply_theme(LIGHT_THEME)

    def init_ui(self):
        self.setWindowTitle("Manga Downloader")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Панель управления темой
        theme_layout = QHBoxLayout()
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Светлая тема", "Тёмная тема"])
        self.theme_selector.currentIndexChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_selector)
        theme_layout.addStretch()
        main_layout.addLayout(theme_layout)

        # Поля ввода
        self.slug_input = QLineEdit()
        self.slug_input.setPlaceholderText("Введите slug URL (пример: 118--hellsing)")
        main_layout.addWidget(self.slug_input)

        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("Номер тома (пример: 1)")
        main_layout.addWidget(self.volume_input)

        self.chapter_input = QLineEdit()
        self.chapter_input.setPlaceholderText("Номер главы (пример: 1)")
        main_layout.addWidget(self.chapter_input)

        # Кнопка загрузки
        self.download_button = QPushButton("Скачать мангу")
        self.download_button.clicked.connect(self.start_download)
        main_layout.addWidget(self.download_button)

        # Логи
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        main_layout.addWidget(self.log_output)

        # Кнопка открытия папки
        self.open_dir_button = QPushButton("Открыть папку с файлами")
        self.open_dir_button.clicked.connect(self.open_directory)
        self.open_dir_button.setEnabled(False)
        main_layout.addWidget(self.open_dir_button)

    def apply_theme(self, style_sheet):
        self.setStyleSheet(style_sheet)
        palette = self.palette()
        if "dark" in style_sheet.lower():
            palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
            self.current_theme = "dark"
        else:
            palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
            self.current_theme = "light"
        self.setPalette(palette)

    def change_theme(self):
        if self.theme_selector.currentText() == "Светлая тема":
            self.apply_theme(LIGHT_THEME)
        else:
            self.apply_theme(DARK_THEME)

    def log_message(self, message, msg_type="info"):
        color_map = {
            "info": QColor("#333333") if self.current_theme == "light" else QColor("#CCCCCC"),
            "success": QColor("#228B22"),
            "error": QColor("#B22222")
        }

        cursor = self.log_output.textCursor()
        format = QTextCharFormat()
        format.setForeground(color_map.get(msg_type, color_map["info"]))
        cursor.setCharFormat(format)
        cursor.insertText(message + "\n")
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)

    def start_download(self):
        slug = self.slug_input.text().strip()
        volume = self.volume_input.text().strip()
        chapter = self.chapter_input.text().strip()

        if not all([slug, volume, chapter]):
            self.log_message("Заполните все поля!", "error")
            return

        self.download_button.setEnabled(False)
        self.open_dir_button.setEnabled(False)
        self.log_message(
            f"[{datetime.now().strftime('%H:%M:%S')}] Начало загрузки: {slug} Том {volume} Глава {chapter}", "info")

        self.thread = DownloadThread(slug, volume, chapter)
        self.thread.log_signal.connect(self.log_message)
        self.thread.finished_signal.connect(self.on_download_finished)
        self.thread.start()

    def on_download_finished(self, save_dir):
        self.download_button.setEnabled(True)
        if save_dir:
            self.last_save_dir = save_dir
            self.open_dir_button.setEnabled(True)
            self.log_message(f"[{datetime.now().strftime('%H:%M:%S')}] Загрузка завершена успешно!", "success")
        else:
            self.log_message(f"[{datetime.now().strftime('%H:%M:%S')}] Загрузка не удалась", "error")

    def open_directory(self):
        if os.path.exists(self.last_save_dir):
            os.startfile(self.last_save_dir)
        else:
            self.log_message("Директория не найдена!", "error")


if __name__ == "__main__":
    app = QApplication([])
    window = MangaDownloaderApp()
    window.show()
    app.exec()
