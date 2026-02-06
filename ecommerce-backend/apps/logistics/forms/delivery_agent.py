from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.logistics.models import DeliveryAgent


class DeliveryAgentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("branch", css_class="col-span-6"),
                Div("user", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("vehicle_number", css_class="col-span-6"),
                Div("vehicle_type", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("status", css_class="col-span-6"),
                Div("capacity", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("current_load", css_class="col-span-6"),
                Div("last_location_at", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("current_lat", css_class="col-span-6"),
                Div("current_lng", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Submit(
                "submit",
                "Save Delivery Agent",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = DeliveryAgent
        fields = (
            "branch",
            "user",
            "vehicle_number",
            "vehicle_type",
            "status",
            "capacity",
            "current_load",
            "current_lat",
            "current_lng",
            "last_location_at",
        )
        widgets = {
            "last_location_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
