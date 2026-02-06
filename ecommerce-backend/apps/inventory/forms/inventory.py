from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.inventory.models import Inventory


class InventoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("variant", css_class="col-span-6"),
                Div("warehouse", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("quantity", css_class="col-span-6"),
                Div("reserved_qty", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("reorder_level", css_class="col-span-6"),
                Div("reorder_qty", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Submit(
                "submit",
                "Save Inventory",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = Inventory
        fields = ("variant", "warehouse", "quantity", "reserved_qty", "reorder_level", "reorder_qty")
