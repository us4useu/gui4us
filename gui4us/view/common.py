import time

from PyQt5.QtCore import *
from PyQt5.QtGui import *


class ViewWorker(QObject):

    def __init__(self, func, interval=0.01):
        super().__init__()
        self.func = func
        self.is_working = False
        self.interval = interval

    @pyqtSlot()
    def run(self):
        # TODO sync point
        self.is_working = True
        while self.is_working:
            self.func()
            time.sleep(self.interval)

    def stop(self):
        self.is_working = False

    def wait_for_stop(self):
        while True:
            # TODO replace active waiting with signal
            if self.is_working:
                time.sleep(0.01)
