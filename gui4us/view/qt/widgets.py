from dataclasses import dataclass
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import (
    QLabel,
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
import numpy as np


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


class Label(Widget):

    def __init__(self, label):
        super().__init__(QLabel(label))

    def set_text(self, text):
        self.backend_widget.setText(text)


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

    def __init__(self, value_range, step, init_value,
                 resolution=None,
                 on_change=None,
                 line_edit_read_only=True,
                 data_type="int"):
        if data_type == "int":
            spin_box = QSpinBox()
            step = step  # chosen arbitrarily
        elif data_type == "float" or data_type == np.float32:
            spin_box = QDoubleSpinBox()
            step = step  # chosen arbitrarily
        else:
            raise ValueError(f"Unrecognized data type: {data_type}")
        super().__init__(spin_box)
        minimum, maximum = value_range
        spin_box.setRange(minimum, maximum)
        spin_box.setSingleStep(step)
        spin_box.setValue(init_value)
        if line_edit_read_only:
            spin_box.lineEdit().setReadOnly(False)
        if on_change is not None:
            spin_box.valueChanged.connect(on_change)

    def set_on_change(self, func, disable_on_change=True):
        def func_wrapper(*args, **kwargs):
            if disable_on_change:
                self.backend_widget.setDisabled(True)
            func(*args, **kwargs)
            if disable_on_change:
                self.backend_widget.setDisabled(False)
            self.backend_widget.setFocus()
        self.backend_widget.valueChanged.connect(func_wrapper)

    def get_value(self):
        self.backend_widget.value()


class Slider(Widget):

    def __init__(self, value_range, init_value, resolution=100,
                 on_change=None,
                 data_type="int"):
        super().__init__(QSlider(Qt.Horizontal))
        self.vmin, self.vmax = value_range
        self.step = (self.vmax-self.vmin)/resolution
        # range
        self.backend_widget.setMinimum(self.to_qslider_value(self.vmin))
        self.backend_widget.setMaximum(self.to_qslider_value(self.vmax))
        # value
        self.backend_widget.setValue(self.to_qslider_value(init_value))
        # Do not signal each slider move
        self.backend_widget.setTracking(False)
        if on_change is not None:
            self.set_on_change(on_change)

    def set_on_change(self, func, disable_on_change=True):
        def func_wrapper(*args, **kwargs):
            if disable_on_change:
                self.backend_widget.setDisabled(True)
            # Convert to real values.
            func(self.get_value())
            if disable_on_change:
                self.backend_widget.setDisabled(False)
            self.backend_widget.setFocus()
        self.backend_widget.valueChanged.connect(func_wrapper)

    def get_value(self):
        return self.to_real_value(self.backend_widget.value())

    def to_qslider_value(self, value):
        # real value -> qslider value (the number of steps)
        # QSlider accepts only integer values
        # so, the QSlider will store only the number of steps
        # vmin = step 0
        # vmax = last step
        value = (value-self.vmin)/self.step
        return int(round(value))

    def to_real_value(self, value):
        return value*self.step + self.vmin


class WidgetSequence(Form):

    def __init__(self, parent, widget_type, label, **params):
        super().__init__(parent)
        self.widgets = []
        init_value = params["init_value"]
        for l, v in zip(label, init_value):
            widget_params = params.copy()
            widget_params["init_value"] = v
            widget = widget_type(**widget_params)
            self.add_field(FormField(l, widget))
            self.widgets.append(widget)

    def set_on_change(self, func):
        # The func should be called if any of the form element will change
        # disable the whole form
        # get value from each form element (sequence)
        # run the func with a vector of the above values
        # enable
        def func_wrapper(*args, **kwargs):
            for widget in self.widgets:
                widget.disable()
            # Get the value of each widget
            value = []
            for widget in self.widgets:
                value.append(widget.get_value())
            func(value)
            for widget in self.widgets:
                widget.enable()
            # Convert to real values.
        for widget in self.widgets:
            widget.set_on_change(func_wrapper, disable_on_change=False)


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
