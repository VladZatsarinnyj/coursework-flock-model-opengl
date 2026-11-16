"""Точка входа программы. Запуск: python main.py"""

from aquarium.app import App


def main():
    app = App()
    try:
        app.run()
    finally:
        # Ресурсы освобождаются и при обычном закрытии окна, и при ошибке.
        app.close()


if __name__ == "__main__":
    main()
