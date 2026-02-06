from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.logistics.models import LineHaulTrip


class LineHaulTripForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("trip_number", css_class="col-span-6"),
                Div("vehicle_number", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("origin_hub", css_class="col-span-6"),
                Div("dest_hub", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("driver_name", css_class="col-span-6"),
                Div("status", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("package_count", css_class="col-span-6"),
                Div("total_weight", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("scheduled_departure", css_class="col-span-6"),
                Div("actual_departure", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("scheduled_arrival", css_class="col-span-6"),
                Div("actual_arrival", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Submit(
                "submit", "Save Trip", css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            ),
        )

    class Meta:
        model = LineHaulTrip
        fields = (
            "trip_number",
            "origin_hub",
            "dest_hub",
            "vehicle_number",
            "driver_name",
            "status",
            "package_count",
            "total_weight",
            "scheduled_departure",
            "actual_departure",
            "scheduled_arrival",
            "actual_arrival",
        )
        widgets = {
            "scheduled_departure": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "actual_departure": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "scheduled_arrival": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "actual_arrival": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
