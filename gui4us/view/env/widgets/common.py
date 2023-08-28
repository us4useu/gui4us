from typing import Callable, Any
import numpy as np

import panel as pn
import param
from panel.viewable import Viewer


class SpinBox(Viewer):

    def __init__(self, data_type, **params):
        if data_type == "int" or data_type == np.int32 or data_type == np.int64:
            self._input = pn.widgets.IntInput(**params)
        elif data_type == "float" or data_type == np.float32 or data_type == np.float64:
            self._input = pn.widgets.FloatInput(**params)
        else:
            raise ValueError(f"Invalid data type: {data_type}")
        super().__init__(**params)

    def __panel__(self) -> pn.viewable.Viewable:
        return self._input

    def on_change(self, clbk: Callable[[Any], None]):

        def internal_callback(event):
            clbk(self._input.value)

        self._input.param.watch(internal_callback, "value")

    @property
    def value(self):
        return self._input.value


class Slider(Viewer):

    def __init__(self, data_type, **params):
        if data_type == "int" or data_type == np.int32 or data_type == np.int64:
            self._input = pn.widgets.EditableIntSlider(**params)
        elif data_type == "float" or data_type == np.float32 or data_type == np.float64:
            self._input = pn.widgets.EditableFloatSlider(**params)
        super().__init__(**params)

    def __panel__(self) -> pn.viewable.Viewable:
        print(self._input)
        return self._input

    def on_change(self, clbk: Callable[[Any], None]):

        def internal_callback(event):
            clbk(self._input.value)

        self._input.param.watch(internal_callback, "value")

    @property
    def value(self):
        return self._input.value


class WidgetSequence(Viewer):

    def __init__(self, widget_type, labels, **params):
        self._inputs = []
        fields = []
        init_value = params["init_value"]
        for l, v in zip(labels, init_value):
            widget_params = params.copy()
            widget_params["init_value"] = v
            widget = widget_type(**widget_params)
            self._inputs.append(widget)
            field = pn.Column(
                pn.pane.Markdown(l),
                widget
            )
            fields.append(field)
        self._layout = pn.Column(*fields)
        super().__init__(**params)

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout

    def on_change(self, clbk: Callable[[Any], None]):
        # The func should be called if any of the form element will change
        # disable the whole form
        # get value from each form element (sequence)
        # run the func with a vector of the above values
        # enable
        def func_wrapper(*args, **kwargs):
            # TODO disable inputs on change
            values = []
            for input in self._inputs:
                values.append(input.value)
            clbk(values)

        for widget in self._inputs:
            widget.on_change(func_wrapper)


