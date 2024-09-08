import gui4us.view.widgets as widgets
from gui4us.view.widgets import *
from gui4us.settings import *
from gui4us.controller.env import *
from gui4us.model import *


class SettingsPanel(Panel):

    def __init__(self, controller: EnvController,
                 title="Settings",
                 custom_presentation=None):
        super().__init__(title)
        if custom_presentation is None:
            custom_presentation = {}
        self.controller = controller
        self.title = title
        self.settings: Sequence[SettingDef] = self.controller.get_settings().get_result()
        self.custom_presentation = custom_presentation
        # Init layout
        self.main_form = Form(self.layout)
        # convert settings to form fields
        for setting in self.settings:
            if isinstance(setting, SettingDef):
                form_field = self._convert_to_field(setting)
                self.main_form.add_field(form_field)

    def _convert_to_field(self, setting: SettingDef):
        label = f"{setting.name}"
        space = setting.space
        if space.unit is not None and setting.space.is_scalar():
            label += f" [{space.unit}]"
        setting_presentation = self.custom_presentation.get(setting.name, None)
        widget = self._convert(setting, setting_presentation)
        return FormField(label=label, widget=widget)

    def _convert(self, setting_def: SettingDef, presentation: SettingPresentation):
        space = setting_def.space
        if not isinstance(space, Box):
            raise ValueError(f"Unsupported space for scalar values: "
                             f"{space}")

        is_scalar = space.is_scalar()
        is_vector = space.is_vector()

        params = {
        "value_range": (space.low, space.high),
            "init_value": setting_def.initial_value,
            "data_type": space.dtype,
        }
        if presentation is not None:
            widget_type = getattr(widgets, presentation.type)
            params = {**params, **presentation.params}
        else:
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
            widget = WidgetSequence(self.layout,
                                    widget_type, dim_names,
                                    **params)
        else:
            raise ValueError("Settings panel supports only scalar and"
                             "vector settings.")

        def setter(value):
            action = setting_def.create_set_action(value)
            self.controller.set(action)

        widget.set_on_change(setter)
        return widget






