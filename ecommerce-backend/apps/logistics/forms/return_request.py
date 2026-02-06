from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.logistics.models import Return


class ReturnForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("return_number", css_class="col-span-6"),
                Div("status", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("order", css_class="col-span-6"),
                Div("order_item", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("reason", css_class="col-span-6"),
                Div("refund_amount", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("reverse_shipment", css_class="col-span-6"),
                Div("approved_at", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("completed_at", css_class="col-span-6"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("reason_text", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(Div("images", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Submit(
                "submit",
                "Save Return",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = Return
        fields = (
            "return_number",
            "order",
            "order_item",
            "status",
            "reason",
            "reason_text",
            "images",
            "refund_amount",
            "reverse_shipment",
            "approved_at",
            "completed_at",
        )
        widgets = {
            "reason_text": forms.Textarea(attrs={"rows": 2}),
            "images": forms.Textarea(attrs={"rows": 2}),  # JSON
            "approved_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "completed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
