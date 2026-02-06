from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.logistics.models import ShipmentTracking


class ShipmentTrackingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("shipment", css_class="col-span-6"),
                Div("status", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("location", css_class="col-span-6"),
                Div("timestamp", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("latitude", css_class="col-span-6"),
                Div("longitude", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("remarks", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Submit(
                "submit",
                "Save Tracking",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = ShipmentTracking
        fields = ("shipment", "status", "location", "remarks", "latitude", "longitude", "timestamp")
        widgets = {
            "remarks": forms.Textarea(attrs={"rows": 2}),
            "timestamp": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
