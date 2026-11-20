"""Точка входа программы. Запуск: python main.py"""

from aquarium.app import App


def main():
    app = App()
    try:
        app.run()
    finally:
        app.close()


if __name__ == "__main__":
    main()
