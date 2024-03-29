import gui4us.view.widgets as widgets
from gui4us.view.widgets import *
from gui4us.settings import *


class SettingsPanel(Panel):

    def __init__(self, controller, title="Settings", settings=None,
                 custom_presentation=None):
        super().__init__(title)
        if custom_presentation is None:
            custom_presentation = {}
        self.controller = controller
        self.title = title
        self.settings = settings
        self.custom_presentation = custom_presentation

        # Init layout
        self.main_form = Form(self.layout)
        # convert settings to form fields
        for setting in self.settings:
            form_field = self.__convert_to_field(setting)
            self.main_form.add_field(form_field)

    def __convert_to_field(self, setting):
        # Label
        # TODO i18n
        label = f"{setting.id}"
        if setting.unit is not None:
            label += f" [{setting.unit}]"
        # Widget
        setting_presentation = self.custom_presentation.get(setting.id, None)
        widget = self.__convert(setting, setting_presentation)
        return FormField(label=label, widget=widget)

    def __convert(self, setting: Setting, presentation: SettingPresentation):
        # TODO discrete set of parameters?
        if not isinstance(setting.domain, ContinuousRange):
            raise ValueError(f"Unsupported domain for scalar values: "
                             f"{setting.domain}")

        is_scalar = setting.is_scalar()
        is_vector = setting.is_vector()

        params = {
            "value_range": (setting.domain.start, setting.domain.end),
            "step": setting.domain.default_step,
            "init_value": setting.init_value,
            "data_type": setting.data_type
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
            widget = widget_type(**params)
        elif is_vector:
            widget = WidgetSequence(self.layout,
                                    widget_type, setting.label, **params)
        else:
            raise ValueError("Settings panel supports only scalar and"
                             "vector settings.")

        def setter(value):
            self.controller.set_setting(setting.id, [value])

        widget.set_on_change(setter)
        return widget






