from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.catalog.models import Category


class CategoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("parent", css_class="col-span-6"),
                Div("name", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("slug", css_class="col-span-6"),
                Div("sort_order", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("icon", css_class="col-span-6"),
                Div("image", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("description", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("attributes", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("is_active", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Submit(
                "submit",
                "Save Category",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = Category
        fields = ("parent", "name", "slug", "description", "icon", "image", "sort_order", "is_active", "attributes")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "attributes": forms.Textarea(attrs={"rows": 3}),  # JSON input
        }
