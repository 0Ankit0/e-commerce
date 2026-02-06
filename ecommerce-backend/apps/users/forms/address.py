from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.users.models import Address


class AddressForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("user", css_class="col-span-6"),
                Div("name", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("phone", css_class="col-span-6"),
                Div("type", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("line1", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("line2", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(
                Div("city", css_class="col-span-6"),
                Div("state", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("pincode", css_class="col-span-6"),
                Div("country", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("landmark", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(
                Div("latitude", css_class="col-span-6"),
                Div("longitude", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("is_default", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Submit(
                "submit",
                "Save Address",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = Address
        fields = (
            "user",
            "name",
            "phone",
            "line1",
            "line2",
            "city",
            "state",
            "pincode",
            "country",
            "landmark",
            "type",
            "is_default",
            "latitude",
            "longitude",
        )
