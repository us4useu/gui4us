from dataclasses import dataclass
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import (
    QPushButton,
    QSlider,
    QSpinBox,
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QDoubleSpinBox
)


@dataclass(frozen=True)
class FormField:
    label: str
    widget: object


class Widget:

    def __init__(self, backend_widget):
        self.backend_widget = backend_widget

    def enable(self):
        self.backend_widget.setEnabled(True)

    def disable(self):
        self.backend_widget.setEnabled(False)


class Form(Widget):

    def __init__(self, parent):
        super().__init__(QFormLayout())
        parent.addLayout(self.backend_widget)

    def add_field(self, field: FormField):
        self.backend_widget.addRow(field.label, field.widget.backend_widget)


class PushButton(Widget):

    def __init__(self, label, onpressed=None):
        super().__init__(QPushButton(label))
        if onpressed is not None:
            self.backend_widget.pressed.connect(onpressed)

    def on_pressed(self, callback):
        self.backend_widget.pressed.connect(callback)

    def set_text(self, text):
        self.backend_widget.setText(text)


class SpinBox(Widget):

    def __init__(self, value_range, step, init_value, on_change=None,
                 line_edit_read_only=True, data_type="int"):
        if data_type == "int":
            spin_box = QSpinBox()
        elif data_type == "float":
            spin_box = QDoubleSpinBox()
        else:
            raise ValueError(f"Unrecognized data type: {data_type}")
        super().__init__(spin_box)
        minimum, maximum = value_range
        spin_box.setRange(minimum, maximum)
        spin_box.setSingleStep(step)
        spin_box.setValue(init_value)
        if line_edit_read_only:
            spin_box.lineEdit().setReadOnly(True)
        if on_change is not None:
            spin_box.valueChanged.connect(on_change)

    def set_on_change(self, func):
        def func_wrapper(*args, **kwargs):
            self.backend_widget.setDisabled(True)
            func(*args, **kwargs)
            self.backend_widget.setDisabled(False)
            self.backend_widget.setFocus()
        self.backend_widget.valueChanged.connect(func_wrapper)

    def get_value(self):
        self.backend_widget.value()


class Slider(Widget):

    def __init__(self, value_range, init_value, precision=2,
                 on_change=None):
        super().__init__(QSlider(Qt.Horizontal))

        def rescale(value):
            return int(round(value * (10**precision)))
        # range
        self.backend_widget.setMinimum(rescale(value_range[0]))
        self.backend_widget.setMaximum(rescale(value_range[1]))
        # value
        self.backend_widget.setValue(rescale(init_value))
        # Do not signal each slider move
        self.backend_widget.setTracking(False)
        if on_change is not None:
            self.backend_widget.valueChanged.connect(on_change)

    def set_on_change(self, func):
        def func_wrapper(*args, **kwargs):
            self.backend_widget.setDisabled(True)
            func(*args, **kwargs)
            self.backend_widget.setDisabled(False)
            self.backend_widget.setFocus()
        self.backend_widget.valueChanged.connect(func_wrapper)

    def get_value(self):
        self.backend_widget.value()


class WidgetSequence(Form):

    def __init__(self, parent, widget_type, labels, **params):
        super().__init__(parent)
        for l in labels:
            widget = widget_type(**params)
            self.add_field(l, widget)


class Panel:

    def __init__(self, title, layout="v"):
        self.backend_widget = QGroupBox(title)
        if layout == "v":
            self.layout = QVBoxLayout()
        elif layout == "h":
            self.layout = QHBoxLayout()
        self.backend_widget.setLayout(self.layout)

    def add_component(self, component):
        self.layout.addWidget(component.backend_widget)

    def disable(self):
        self.backend_widget.setEnabled(False)

    def enable(self):
        self.backend_widget.setEnabled(True)


def show_error_message(msg):
    box = QMessageBox()
    box.setIcon(QMessageBox.Critical)
    box.setText(msg)
    box.setWindowTitle("Error")
    box.setStandardButtons(QMessageBox.Ok)
    box.exec_()
