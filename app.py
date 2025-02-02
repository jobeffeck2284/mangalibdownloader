import logging
import os
import sys
from datetime import datetime

import requests
from PIL import Image
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import (
    QColor, QTextCursor, QTextCharFormat, QPalette, QPixmap,
    QAction
)
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QWidget, QComboBox, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QSplitter, QDialog,
    QMessageBox, QMenu, QTreeWidget, QTreeWidgetItem, QFileDialog
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('manga_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Обновлённые стили
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
    QTableWidget {
        gridline-color: #E0E0E0;
        font-size: 13px;
        border: 1px solid #E0E0E0;
        border-radius: 6px;
    }
    QHeaderView::section {
        background-color: #F8F9FA;
        padding: 8px;
        border: none;
        border-bottom: 2px solid #E0E0E0;
        font-weight: 500;
    }
    QTableWidget::item {
        padding: 6px;
    }
    QTableWidget::item:selected {
        background-color: #FF6B35;
        color: white;
    }
    QLineEdit[readOnly="true"] {
        background-color: #F8F9FA;
        color: #666666;
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
    QTableWidget {
        gridline-color: #404040;
        font-size: 13px;
        border: 1px solid #404040;
        border-radius: 6px;
    }
    QHeaderView::section {
        background-color: #353535;
        padding: 8px;
        border: none;
        border-bottom: 2px solid #404040;
        font-weight: 500;
    }
    QTableWidget::item:selected {
        background-color: #FF6B35;
        color: white;
    }
    QLineEdit[readOnly="true"] {
        background-color: #404040;
        color: #AAAAAA;
    }
"""

def excepthook(exctype, value, traceback):
    logging.error("Uncaught exception:", exc_info=(exctype, value, traceback))
    QMessageBox.critical(None, "Критическая ошибка", str(value))

sys.excepthook = excepthook

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

    def __init__(self, slug_url, volume_number, chapter_number, save_directory, parent=None):
        super().__init__(parent)
        self.slug_url = slug_url
        self.volume_number = volume_number
        self.chapter_number = chapter_number
        self.save_directory = save_directory

    def run(self):
        try:
            self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Начало загрузки...", "info")

            folder_name = sanitize_folder_name(self.slug_url.split("--", 1)[-1])
            volume_folder = f"Volume_{self.volume_number}"
            chapter_folder = f"Chapter_{self.chapter_number}"

            save_dir = os.path.join(
                self.save_directory,
                folder_name,
                volume_folder,
                chapter_folder
            )
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


class MangaSearchThread(QThread):
    search_complete = pyqtSignal(list)

    def __init__(self, search_query):
        super().__init__()
        self.search_query = search_query

    def run(self):
        try:
            params = {
                "site_id[]": 1,
                "q": self.search_query,
                "page": 1,
                "status[]": [1, 2, 4],
                "types[]": [1, 5]
            }

            response = requests.get("https://api.lib.social/api/manga", params=params, timeout=10)  # Добавлен таймаут
            response.raise_for_status()  # Проверка HTTP ошибок
            data = response.json()
            self.search_complete.emit(data.get('data', []))
        except Exception as e:
            print(f"Search error: {str(e)}")  # Логирование ошибки
            self.search_complete.emit([])


class ImageLoaderThread(QThread):
    image_loaded = pyqtSignal(str, QPixmap)
    error_occurred = pyqtSignal(str, str)  # Новый сигнал для ошибок

    def __init__(self, url, manga_id):
        super().__init__()
        self.url = url
        self.manga_id = manga_id

    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()  # Проверка HTTP статуса

            img_data = response.content
            pixmap = QPixmap()
            if not pixmap.loadFromData(img_data):
                raise ValueError("Неверный формат изображения")

            self.image_loaded.emit(
                self.manga_id,
                pixmap.scaled(100, 150, Qt.AspectRatioMode.KeepAspectRatio)
            )
        except Exception as e:
            self.error_occurred.emit(
                self.manga_id,
                f"Ошибка загрузки обложки: {str(e)}"
            )


class MangaDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_theme = "light"
        self.last_save_dir = ""
        self.manga_cache = {}
        self.chapter_threads = []  # Добавьте эту строку
        self.loader_threads = []  # Список для хранения ссылок на потоки
        self.init_ui()
        self.apply_theme(LIGHT_THEME)

    def init_ui(self):
        self.setWindowTitle("Manga Downloader")
        self.setGeometry(100, 100, 1000, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # Верхняя панель поиска
        search_panel = QWidget()
        search_layout = QVBoxLayout(search_panel)

        # Панель управления темой
        theme_layout = QHBoxLayout()
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Светлая тема", "Тёмная тема"])
        self.theme_selector.currentIndexChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_selector)
        theme_layout.addStretch()
        search_layout.addLayout(theme_layout)

        # Поле поиска
        search_control_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск манги по названию...")
        search_control_layout.addWidget(self.search_input)

        self.search_button = QPushButton("Поиск")
        self.search_button.clicked.connect(self.start_search)
        search_control_layout.addWidget(self.search_button)
        search_layout.addLayout(search_control_layout)

        # Таблица результатов
        self.manga_table = QTableWidget()
        self.manga_table.setColumnCount(5)  # Изменено с 4 на 5
        self.manga_table.setHorizontalHeaderLabels(["Обложка", "Название", "Тип", "Статус", "Slug URL"])  # Добавлен новый столбец
        self.manga_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # Изменён режим изменения размеров
        self.manga_table.verticalHeader().setVisible(False)
        self.manga_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.manga_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # Включаем контекстное меню
        self.manga_table.customContextMenuRequested.connect(self.show_context_menu)
        search_layout.addWidget(self.manga_table)

        # Нижняя панель загрузки
        download_panel = QWidget()
        download_layout = QVBoxLayout(download_panel)

        directory_layout = QHBoxLayout()
        self.directory_input = QLineEdit()
        self.directory_input.setReadOnly(True)
        self.directory_input.setPlaceholderText("Папка для сохранения не выбрана")
        self.directory_button = QPushButton("Выбрать папку")
        self.directory_button.clicked.connect(self.select_directory)
        directory_layout.addWidget(self.directory_input)
        directory_layout.addWidget(self.directory_button)
        download_layout.insertLayout(0, directory_layout)  # Добавляем в начало

        # Поля ввода
        input_layout = QVBoxLayout()
        self.slug_input = QLineEdit()
        self.slug_input.setPlaceholderText("Slug URL (пример: 118--hellsing)")
        input_layout.addWidget(self.slug_input)

        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("Номер тома")
        input_layout.addWidget(self.volume_input)

        self.chapter_input = QLineEdit()
        self.chapter_input.setPlaceholderText("Номер главы")
        input_layout.addWidget(self.chapter_input)
        download_layout.addLayout(input_layout)

        # Кнопки
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Скачать мангу")
        self.download_button.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_button)

        self.open_dir_button = QPushButton("Открыть папку")
        self.open_dir_button.clicked.connect(self.open_directory)
        self.open_dir_button.setEnabled(False)
        button_layout.addWidget(self.open_dir_button)
        download_layout.addLayout(button_layout)

        # Логи
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        download_layout.addWidget(self.log_output)

        main_splitter.addWidget(search_panel)
        main_splitter.addWidget(download_panel)
        main_splitter.setSizes([400, 400])

        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(main_splitter)

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if directory:
            self.save_directory = directory
            self.directory_input.setText(directory)
            settings = QSettings("MangaDownloader", "AppSettings")
            settings.setValue("save_directory", directory)



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
        if not self.save_directory:
            self.log_message("Сначала выберите папку для сохранения!", "error")
            return

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

        self.thread = DownloadThread(slug, volume, chapter, self.save_directory)
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

    def start_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        self.search_thread = MangaSearchThread(query)
        self.search_thread.search_complete.connect(self.display_results)
        self.search_thread.start()

    def update_cover(self, slug_url, pixmap):
        """ Обновляет изображение в таблице после загрузки """
        for row in range(self.manga_table.rowCount()):
            item = self.manga_table.item(row, 1)  # Столбец с названием манги
            if item and item.data(Qt.ItemDataRole.UserRole) == slug_url:
                label = self.manga_table.cellWidget(row, 0)
                if isinstance(label, QLabel):
                    label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation))

                    # Автоматически подстраиваем размер столбца под изображение
                    self.manga_table.setColumnWidth(0, pixmap.width())
                break

    def display_results(self, manga_list):
        try:
            self.manga_table.setRowCount(len(manga_list))
            self.manga_cache.clear()
            row_height = 160  # Высота строки = высота изображения + отступы

            for row, manga in enumerate(manga_list):
                self.manga_table.setRowHeight(row, row_height)  # Установка фиксированной высоты

                # Создаем QLabel с фиксированным размером
                image_label = QLabel()
                image_label.setFixedSize(120, 150)  # Увеличим ширину для лучшего отображения
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                image_label.setStyleSheet("""
                    QLabel {
                        background-color: #F8F9FA;
                        border-radius: 4px;
                        padding: 4px;
                    }
                """)
                self.manga_table.setCellWidget(row, 0, image_label)

                cover_url = ""
                if isinstance(manga.get('cover'), dict):
                    cover_url = manga['cover'].get('md') or manga['cover'].get('default') or ""

                image_label = QLabel()
                image_label.setFixedSize(100, 150)  # Начальный размер
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                image_label.setScaledContents(True)  # Позволяет масштабировать изображение
                self.manga_table.setCellWidget(row, 0, image_label)

                if cover_url and cover_url.startswith(('http://', 'https://')):
                    loader = ImageLoaderThread(cover_url, manga['slug_url'])
                    loader.image_loaded.connect(self.update_cover)
                    loader.finished.connect(lambda l=loader: self.loader_threads.remove(l))
                    self.loader_threads.append(loader)
                    loader.start()
                else:
                    placeholder = QPixmap(100, 150)
                    placeholder.fill(QColor(200, 200, 200))
                    image_label.setPixmap(placeholder)

                name = manga.get('rus_name') or manga.get('eng_name') or manga.get('name', '')
                name_item = QTableWidgetItem(name)
                name_item.setData(Qt.ItemDataRole.UserRole, manga['slug_url'])
                self.manga_table.setItem(row, 1, name_item)

                type_item = QTableWidgetItem(manga['type'].get('label', 'N/A'))
                status_item = QTableWidgetItem(manga['status'].get('label', 'N/A'))
                self.manga_table.setItem(row, 2, type_item)
                self.manga_table.setItem(row, 3, status_item)

                slug_item = QTableWidgetItem(manga['slug_url'])
                slug_item.setData(Qt.ItemDataRole.UserRole, manga['slug_url'])
                self.manga_table.setItem(row, 4, slug_item)

            # Настройка внешнего вида таблицы
            self.manga_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
            self.manga_table.verticalHeader().setDefaultSectionSize(row_height)
            self.manga_table.setShowGrid(False)

        except Exception as e:
            print(f"Display error: {str(e)}")

    def show_context_menu(self, pos):
        try:
            item = self.manga_table.itemAt(pos)
            if not item:
                return

            row = self.manga_table.rowAt(pos.y())
            slug_url = self.manga_table.item(row, 1).data(Qt.ItemDataRole.UserRole)

            menu = QMenu()

            # Добавляем пункт для глав в любое место таблицы
            chapters_action = QAction("Открыть список глав", self)
            chapters_action.triggered.connect(lambda: self.load_chapters(slug_url))
            menu.addAction(chapters_action)

            # Для колонки slug URL добавляем копирование
            if self.manga_table.columnAt(pos.x()) == 4:
                copy_action = QAction("Копировать Slug URL", self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(item.text()))
                menu.addAction(copy_action)

            menu.exec(self.manga_table.viewport().mapToGlobal(pos))

        except Exception as e:
            logger.error(f"Context menu error: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка в контекстном меню:\n{str(e)}")

    def copy_to_clipboard(self, text):
        try:
            logging.debug(f"Attempting to copy text: {text}")
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(text)
            logging.info("Text copied to clipboard successfully")

        except Exception as e:
            logging.error("Clipboard error:", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка копирования:\n{str(e)}")

    def update_cover(self, slug_url, pixmap):
        for row in range(self.manga_table.rowCount()):
            if self.manga_table.item(row, 1).data(Qt.ItemDataRole.UserRole) == slug_url:
                label = self.manga_table.cellWidget(row, 0)
                if isinstance(label, QLabel):
                    # Масштабируем изображение с сохранением пропорций
                    scaled_pixmap = pixmap.scaled(
                        label.width(), label.height(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    label.setPixmap(scaled_pixmap)

                    # Центрируем изображение
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                break

    # Добавим новые методы для загрузки и отображения глав
    def load_chapters(self, slug_url):
        self.log_message(f"[{datetime.now().strftime('%H:%M:%S')}] Загрузка глав...", "info")
        thread = ChaptersLoaderThread(slug_url)
        thread.chapters_loaded.connect(self.show_chapters_dialog)
        thread.error_occurred.connect(lambda e: self.log_message(e, "error"))

        # Добавляем проверку перед удалением
        def safe_remove():
            if thread in self.chapter_threads:
                self.chapter_threads.remove(thread)

        thread.finished.connect(safe_remove)  # Используем функцию с проверкой
        self.chapter_threads.append(thread)
        thread.start()

    def show_chapters_dialog(self, chapters):
        dialog = ChaptersDialog(self)

        # Группируем главы по томам
        volumes = {}
        for chapter in chapters:
            vol = chapter.get('volume', 'Без тома')
            if vol not in volumes:
                volumes[vol] = []
            volumes[vol].append(chapter)

        # Заполняем дерево
        for volume, chapters in volumes.items():
            volume_item = QTreeWidgetItem(dialog.tree, [str(volume)])
            for chap in chapters:
                chapter_number = chap.get('number', 'N/A')
                name = chap.get('name', 'Без названия') or 'Без названия'
                QTreeWidgetItem(volume_item, [str(volume), chapter_number, name])

        dialog.tree.expandAll()
        dialog.exec()


# Добавим новый класс потока для загрузки глав
class ChaptersLoaderThread(QThread):
    chapters_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, slug_url):
        super().__init__()
        self.slug_url = slug_url

    def run(self):
        try:
            url = f"https://api.lib.social/api/manga/{self.slug_url}/chapters"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.chapters_loaded.emit(data.get('data', []))
        except Exception as e:
            self.error_occurred.emit(f"Ошибка загрузки глав: {str(e)}")
        finally:
            self.finished.emit()  # Добавьте этот вызов в блок finally


# Добавим новый диалог для отображения глав
class ChaptersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Тома и главы")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Том", "Глава", "Название"])
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tree)


if __name__ == "__main__":
    app = QApplication([])
    window = MangaDownloaderApp()
    window.show()
    app.exec()
