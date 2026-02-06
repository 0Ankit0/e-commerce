from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.orders.models import Cart


class CartForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("user", css_class="col-span-6"),
                Div("session_id", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Submit(
                "submit", "Save Cart", css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            ),
        )

    class Meta:
        model = Cart
        fields = ("user", "session_id")
