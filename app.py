import os
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLineEdit, QPushButton, QTextEdit, QFileDialog, QWidget, QMenu
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

def get_manga_pages(slug_url, volume_number, chapter_number):
    base_url = "https://api.lib.social/api/manga"
    endpoint = f"{base_url}/{slug_url}/chapter"
    params = {
        "number": chapter_number,
        "volume": volume_number
    }

    response = requests.get(endpoint, params=params)

    if response.status_code == 200:
        data = response.json()
        pages = data.get("data", {}).get("pages", [])
        return [
            f"https://img33.imgslib.link{page['url']}" \
            if page["url"].startswith("//manga/") else page["url"]
            for page in pages
        ]
    else:
        return []

def save_images(image_urls, save_dir, logger):
    os.makedirs(save_dir, exist_ok=True)
    for i, url in enumerate(image_urls, start=1):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                image_path = os.path.join(save_dir, f"{i:03}.jpg")
                with open(image_path, "wb") as img_file:
                    for chunk in response.iter_content(1024):
                        img_file.write(chunk)
                logger.append(f"Сохранено: {image_path} (Источник: {url})")
            else:
                logger.append(f"Ошибка загрузки: {url} (Статус: {response.status_code})")
        except requests.exceptions.RequestException as e:
            logger.append(f"Ошибка подключения к {url}: {e}")

class MangaDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Manga Downloader")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.slug_input = QLineEdit()
        self.slug_input.setPlaceholderText("Введите slug URL манги")
        self.layout.addWidget(self.slug_input)

        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("Введите номер тома")
        self.layout.addWidget(self.volume_input)

        self.chapter_input = QLineEdit()
        self.chapter_input.setPlaceholderText("Введите номер главы")
        self.layout.addWidget(self.chapter_input)

        self.download_button = QPushButton("Скачать мангу")
        self.download_button.clicked.connect(self.download_manga)
        self.layout.addWidget(self.download_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.layout.addWidget(self.log_output)

        self.open_dir_button = QPushButton("Открыть директорию")
        self.open_dir_button.clicked.connect(self.open_directory)
        self.open_dir_button.setEnabled(False)
        self.layout.addWidget(self.open_dir_button)

        self.create_actions()

    def create_actions(self):
        self.slug_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.slug_input.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, self.slug_input)
        )

        self.volume_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.volume_input.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, self.volume_input)
        )

        self.chapter_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chapter_input.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, self.chapter_input)
        )

    def show_context_menu(self, pos, widget):
        menu = QMenu(self)
        paste_action = menu.addAction("Вставить")
        paste_action.triggered.connect(lambda: self.paste_clipboard(widget))
        menu.exec(widget.mapToGlobal(pos))

    def paste_clipboard(self, widget):
        clipboard = QApplication.clipboard()
        widget.setText(clipboard.text())

    def download_manga(self):
        slug_url = self.slug_input.text().strip()
        volume_number = self.volume_input.text().strip()
        chapter_number = self.chapter_input.text().strip()

        if not slug_url or not volume_number or not chapter_number:
            self.log_output.append("Пожалуйста, заполните все поля.")
            return

        self.log_output.append("Скачивание страниц...")
        page_urls = get_manga_pages(slug_url, volume_number, chapter_number)
        if page_urls:
            save_dir = os.path.join(os.path.dirname(__file__), "manga")
            logger = []
            save_images(page_urls, save_dir, logger)
            self.log_output.append("\n".join(logger))
            self.open_dir_button.setEnabled(True)
        else:
            self.log_output.append("Не удалось получить страницы манги.")

    def open_directory(self):
        save_dir = os.path.join(os.path.dirname(__file__), "manga")
        QFileDialog.getOpenFileName(self, "Открыть директорию", save_dir)

if __name__ == "__main__":
    app = QApplication([])

    app.setStyle("Fusion")

    window = MangaDownloaderApp()
    window.show()

    app.exec()
