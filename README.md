# Mangalib Downloader

Этот проект позволяет скачивать страницы манги с использованием графического интерфейса на PyQt6. Он очень простой и написан при помощи ChatGPT, в будущем добавлю чуть больше функций. При "зависании" программы не пугайтесь, я пока не добавил, поддержку асинхронных действий и при скачивании возникает зависание интерфейса, но можно заметить что странницы скачиваются.

slug URL в программе это id манги

Пример:

Вот манга Домашняя девушка: https://mangalib.me/ru/manga/4852--domestic-na-kanojo. В данном случае slug URL является 4852--domestic-na-kanojo.

## Требования

Перед запуском приложения убедитесь, что у вас установлен Python версии 3.6 или выше.

### Установка Python

1. Скачайте и установите Python с официального сайта:
   - [Python Downloads](https://www.python.org/downloads/)

2. Убедитесь, что Python установлен правильно, выполнив в терминале или командной строке:
   ```bash
   python --version
### Установка зависимостей

После установки Python вам нужно будет установить зависимости, указанные в файле requirements.txt

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/jobeffeck2284/mangalibdownloader.git
   cd mangalibdownloader
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
### Установка зависимостей

После установки всех зависимостей, вы можете запустить приложение:
   ```bash
   python app.py


