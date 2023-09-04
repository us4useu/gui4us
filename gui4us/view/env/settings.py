import panel as pn

from gui4us.settings import *
from gui4us.controller.env import *
from gui4us.model import *
from gui4us.view.env.widgets import Slider, SpinBox, WidgetSequence


# class SettingsPanel(pn.viewable.Viewer):
#
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         widgets = [pn.pane.Markdown("**Voltage [V]**")]
#         widgets.append(
#             pn.widgets.IntInput(value=5, step=5, start=5, stop=90)
#         )
#         widgets.append(pn.pane.Markdown("**TGC [dB]**"))
#         for i in range(5):
#             slider = pn.widgets.EditableFloatSlider(
#             name=f"{i*10} [mm]", start=14, end=54, step=0.1, value=34)
#             widgets.append(slider)
#         self._layout = pn.Column(
#             *widgets,
#             sizing_mode="stretch_both"
#         )
#
#     def __panel__(self) -> pn.viewable.Viewable:
#         return self._layout
#

class SettingsPanel(pn.viewable.Viewer):

    def __init__(self, controller: EnvironmentController, displays, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        settings = self.controller.get_settings()
        self.settings: Sequence[SettingDef] = settings.get_result()  # NOTE: must be list
        self.setters = [self.controller.set]*len(self.settings)
        for d in displays:
            self.settings.extend(d.get_settings())
            self.setters.extend(d.get_setters())

        # convert settings to form fields
        self.fields = self._create_fields(self.settings, self.setters)
        self._layout = pn.Column(*self.fields, sizing_mode="stretch_both")

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout

    def _create_fields(self, settings: Sequence[SettingDef], setters):
        fields = []
        for setting, setter in zip(settings, setters):
            if isinstance(setting, SettingDef):
                fields.append(self._convert_to_field(setting, setter))
        return fields

    def _convert_to_field(self, setting: SettingDef, setter):
        label = f"**{setting.name}**"
        space = setting.space
        if space.unit is not None and setting.space.is_scalar():
            label += f" [{space.unit}]"
        widget = self._convert(setting, setter)
        return pn.Column(
            pn.pane.Markdown(label),
            widget,
        )

    def _convert(self, setting_def: SettingDef, setting_setter):
        space = setting_def.space
        if not isinstance(space, Box):
            raise ValueError(f"Unsupported space for scalar values: "
                             f"{space}")

        is_scalar = space.is_scalar()
        is_vector = space.is_vector()

        params = {
            "start": space.low,
            "end": space.high,
            "value": setting_def.initial_value,
            "data_type": space.dtype
        }
        if is_scalar:
            widget_type = SpinBox
        else:
            widget_type = Slider
        if is_scalar:
            params["step"] = setting_def.step
            widget = widget_type(**params)
        elif is_vector:
            dim_names = setting_def.space.name
            dim_units = setting_def.space.unit
            if dim_units is not None:
                dim_names = [f"{n} [{u}]" for n, u in zip(dim_names, dim_units)]
            # TODO(pjarosik)
            widget = WidgetSequence(
                widget_type=widget_type,
                labels=dim_names,
                **params
            )
        else:
            raise ValueError("Settings panel supports only scalar and "
                             "vector settings.")

        def setter(value):
            action = setting_def.create_set_action(value)
            setting_setter(action)

        widget.on_change(setter)
        return widget






