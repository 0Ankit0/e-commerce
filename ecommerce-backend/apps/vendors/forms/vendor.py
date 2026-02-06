from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.vendors.models import Vendor


class VendorForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("business_name", css_class="col-span-6"),
                Div("display_name", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("slug", css_class="col-span-6"),
                Div("gstin", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("pan", css_class="col-span-6"),
                Div("status", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("commission_tier", css_class="col-span-6"),
                Div("rating", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("logo", css_class="col-span-6"),
                Div("banner", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("approved_at", css_class="col-span-6"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("description", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Submit(
                "submit",
                "Save Vendor",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = Vendor
        fields = (
            "business_name",
            "display_name",
            "slug",
            "description",
            "logo",
            "banner",
            "gstin",
            "pan",
            "status",
            "rating",
            "commission_tier",
            "approved_at",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "approved_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
