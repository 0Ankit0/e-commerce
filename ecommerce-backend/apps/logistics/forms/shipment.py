from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.logistics.models import Shipment

class ShipmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('awb', css_class='col-span-6'),
                Div('status', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('order', css_class='col-span-6'),
                Div('vendor_order', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('vendor', css_class='col-span-6'),
                Div('type', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('warehouse', css_class='col-span-4'),
                Div('branch', css_class='col-span-4'),
                Div('agent', css_class='col-span-4'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('weight', css_class='col-span-6'),
                Div('declared_value', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('is_cod', css_class='col-span-6'),
                Div('cod_amount', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('picked_up_at', css_class='col-span-6'),
                Div('delivered_at', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('dimensions', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Shipment', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = Shipment
        fields = (
            "awb", "order", "vendor_order", "vendor", "warehouse", 
            "branch", "agent", "status", "type", "weight", 
            "dimensions", "declared_value", "is_cod", "cod_amount", 
            "picked_up_at", "delivered_at"
        )
        widgets = {
            "dimensions": forms.Textarea(attrs={"rows": 2}),
            "picked_up_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "delivered_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
