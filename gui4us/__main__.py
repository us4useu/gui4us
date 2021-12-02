from gui4us.model import MockedModel, ArrusModel
from PyQt5.QtWidgets import QApplication
import sys
from gui4us.controller import Controller
from gui4us.view import MainWindow

__version__ = "0.0.1"
NAME = "GUI4us"


def close_model_and_controller(model, controller):
    if model is not None:
        try:
            model.close()
        except Exception as e:
            logging.exception(e)
        try:
            controller.close()
        except Exception as e:
            logging.exception(e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    model = None
    controller = None
    try:
        model = ArrusModel(settings_path=sys.argv[1])
        controller = Controller(model)
        window = MainWindow(f"{NAME} {__version__}", controller=controller)
        window.show()
        sys.exit(app.exec_())
    finally:
        close_model_and_controller(model, controller)