from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.catalog.models import Brand


class BrandForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("name", css_class="col-span-6"),
                Div("slug", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("logo", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("description", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("is_active", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Submit(
                "submit", "Save Brand", css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            ),
        )

    class Meta:
        model = Brand
        fields = ("name", "slug", "logo", "description", "is_active")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
