from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.orders.models import Order

class OrderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('order_number', css_class='col-span-6'),
                Div('user', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('address', css_class='col-span-6'),
                Div('status', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('payment_method', css_class='col-span-6'),
                Div('payment_status', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('subtotal', css_class='col-span-4'),
                Div('discount', css_class='col-span-4'),
                Div('shipping_charge', css_class='col-span-4'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('tax', css_class='col-span-6'),
                Div('total', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('confirmed_at', css_class='col-span-3'),
                Div('shipped_at', css_class='col-span-3'),
                Div('delivered_at', css_class='col-span-3'),
                Div('cancelled_at', css_class='col-span-3'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('notes', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Order', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = Order
        fields = (
            "order_number", "user", "address", "status", "payment_method", 
            "payment_status", "subtotal", "discount", "shipping_charge", 
            "tax", "total", "notes", "confirmed_at", "shipped_at", 
            "delivered_at", "cancelled_at"
        )
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "confirmed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "shipped_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "delivered_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "cancelled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
