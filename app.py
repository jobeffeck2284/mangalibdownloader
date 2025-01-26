import os
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLineEdit, QPushButton, QTextEdit, QFileDialog, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PIL import Image

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

def sanitize_folder_name(name):
    return name.replace("-", "_").replace(" ", "_")

class DownloadThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def __init__(self, slug_url, volume_number, chapter_number, parent=None):
        super().__init__(parent)
        self.slug_url = slug_url
        self.volume_number = volume_number
        self.chapter_number = chapter_number

    def run(self):
        folder_name = sanitize_folder_name(self.slug_url.split("--", 1)[-1])
        volume_folder = f"Volume {self.volume_number}"
        chapter_folder = f"Chapter {self.chapter_number}"

        save_dir = os.path.join(os.path.dirname(__file__), "manga", folder_name, volume_folder, chapter_folder)
        os.makedirs(save_dir, exist_ok=True)

        self.log_signal.emit("Скачивание страниц...")
        page_urls = get_manga_pages(self.slug_url, self.volume_number, self.chapter_number)
        image_paths = []

        if page_urls:
            for i, url in enumerate(page_urls, start=1):
                try:
                    response = requests.get(url, stream=True)
                    if response.status_code == 200:
                        image_path = os.path.join(save_dir, f"{i:03}.jpg")
                        with open(image_path, "wb") as img_file:
                            for chunk in response.iter_content(1024):
                                img_file.write(chunk)
                        image_paths.append(image_path)
                        self.log_signal.emit(f"Сохранено: {image_path} (Источник: {url})")
                    else:
                        self.log_signal.emit(f"Ошибка загрузки: {url} (Статус: {response.status_code})")
                except requests.exceptions.RequestException as e:
                    self.log_signal.emit(f"Ошибка подключения к {url}: {e}")

            if image_paths:
                pdf_path = os.path.join(save_dir, f"Volume {self.volume_number} Chapter {self.chapter_number}.pdf")
                self.create_pdf_with_pillow(image_paths, pdf_path)
                self.log_signal.emit(f"PDF сохранён: {pdf_path}")

            self.finished_signal.emit(save_dir)
        else:
            self.log_signal.emit("Не удалось получить страницы манги.")
            self.finished_signal.emit("")

    def create_pdf_with_pillow(self, image_paths, output_path):
        images = []
        for image_path in image_paths:
            try:
                img = Image.open(image_path).convert("RGB")
                images.append(img)
            except Exception as e:
                self.log_signal.emit(f"Ошибка обработки изображения {image_path}: {e}")

        if images:
            images[0].save(output_path, save_all=True, append_images=images[1:])

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
        self.download_button.clicked.connect(self.start_download)
        self.layout.addWidget(self.download_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.layout.addWidget(self.log_output)

        self.open_dir_button = QPushButton("Открыть директорию")
        self.open_dir_button.clicked.connect(self.open_directory)
        self.open_dir_button.setEnabled(False)
        self.layout.addWidget(self.open_dir_button)

    def start_download(self):
        slug_url = self.slug_input.text().strip()
        volume_number = self.volume_input.text().strip()
        chapter_number = self.chapter_input.text().strip()

        if not slug_url or not volume_number or not chapter_number:
            self.log_output.append("Введите корректные данные.")
            return

        self.download_thread = DownloadThread(slug_url, volume_number, chapter_number)
        self.download_thread.log_signal.connect(self.log_output.append)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.start()
        self.download_button.setEnabled(False)

    def on_download_finished(self, save_dir):
        self.download_button.setEnabled(True)
        if save_dir:
            self.open_dir_button.setEnabled(True)
            self.last_save_dir = save_dir

    def open_directory(self):
        if hasattr(self, "last_save_dir"):
            os.startfile(self.last_save_dir)

if __name__ == "__main__":
    app = QApplication([])

    # Устанавливаем светлую тему
    app.setStyle("Fusion")

    window = MangaDownloaderApp()
    window.show()

    app.exec()