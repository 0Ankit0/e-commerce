from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.orders.models import CartItem


class CartItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("cart", css_class="col-span-6"),
                Div("variant", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("quantity", css_class="col-span-6"),
                Div("price_at_add", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Submit(
                "submit",
                "Save Cart Item",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = CartItem
        fields = ("cart", "variant", "quantity", "price_at_add")
