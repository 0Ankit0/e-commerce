from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.orders.models import VendorOrder

class VendorOrderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('order', css_class='col-span-6'),
                Div('vendor', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('vendor_order_number', css_class='col-span-6'),
                Div('status', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('subtotal', css_class='col-span-4'),
                Div('commission', css_class='col-span-4'),
                Div('vendor_amount', css_class='col-span-4'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('accepted_at', css_class='col-span-6'),
                Div('packed_at', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Vendor Order', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = VendorOrder
        fields = (
            "order", "vendor", "vendor_order_number", "status", 
            "subtotal", "commission", "vendor_amount", 
            "accepted_at", "packed_at"
        )
        widgets = {
            "accepted_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "packed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
