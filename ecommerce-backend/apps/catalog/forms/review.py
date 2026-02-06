from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.catalog.models import Review


class ReviewForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("product", css_class="col-span-6"),
                Div("user", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("order", css_class="col-span-6"),
                Div("rating", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("title", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("content", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("images", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(
                Div("status", css_class="col-span-6"),
                Div("helpful_count", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Submit(
                "submit",
                "Save Review",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = Review
        fields = ("product", "user", "order", "rating", "title", "content", "images", "status", "helpful_count")
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3}),
            "images": forms.Textarea(attrs={"rows": 3}),
        }
