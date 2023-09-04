import panel as pn

from gui4us.settings import *
from gui4us.controller.env import *
from gui4us.model import *
from gui4us.view.env.widgets import Slider, SpinBox, WidgetSequence



class SettingsPanel(pn.viewable.Viewer):

    def __init__(self, controller: EnvironmentController, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        settings = self.controller.get_settings()
        self.settings: Sequence[SettingDef] = settings.get_result()
        # convert settings to form fields
        self.fields = self._create_fields(self.settings)
        self._layout = pn.Column(*self.fields, sizing_mode="stretch_both")

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout

    def _create_fields(self, settings: Sequence[SettingDef]):
        fields = []
        for setting in settings:
            if isinstance(setting, SettingDef):
                fields.append(self._convert_to_field(setting))
        return fields

    def _convert_to_field(self, setting: SettingDef):
        label = f"**{setting.name}**"
        space = setting.space
        if space.unit is not None and setting.space.is_scalar():
            label += f" [{space.unit}]"
        widget = self._convert(setting)
        return pn.Column(
            pn.pane.Markdown(label),
            widget,
        )

    def _convert(self, setting_def: SettingDef):
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
            self.controller.set(action)

        widget.on_change(setter)
        return widget






