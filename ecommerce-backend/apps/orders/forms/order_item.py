from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.orders.models import OrderItem

class OrderItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('order', css_class='col-span-6'),
                Div('vendor_order', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('product', css_class='col-span-6'),
                Div('variant', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('vendor', css_class='col-span-6'),
                Div('product_name', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('variant_name', css_class='col-span-6'),
                Div('status', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('quantity', css_class='col-span-4'),
                Div('unit_price', css_class='col-span-4'),
                Div('total_price', css_class='col-span-4'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('image_url', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Order Item', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = OrderItem
        fields = (
            "order", "vendor_order", "product", "variant", "vendor", 
            "product_name", "variant_name", "image_url", 
            "quantity", "unit_price", "total_price", "status"
        )
