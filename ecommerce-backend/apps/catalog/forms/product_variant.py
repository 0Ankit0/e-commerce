from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.catalog.models import ProductVariant


class ProductVariantForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("product", css_class="col-span-6"),
                Div("sku", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("name", css_class="col-span-6"),
                Div("mrp", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("selling_price", css_class="col-span-6"),
                Div("cost_price", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("weight", css_class="col-span-6"),
                Div("dimensions", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("is_default", css_class="col-span-6"),
                Div("is_active", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("attributes", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Submit(
                "submit",
                "Save Variant",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = ProductVariant
        fields = (
            "product",
            "sku",
            "name",
            "mrp",
            "selling_price",
            "cost_price",
            "attributes",
            "weight",
            "dimensions",
            "is_default",
            "is_active",
        )
        widgets = {
            "attributes": forms.Textarea(attrs={"rows": 2}),
            "dimensions": forms.Textarea(attrs={"rows": 2}),
        }
