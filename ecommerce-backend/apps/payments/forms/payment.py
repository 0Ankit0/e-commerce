from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.payments.models import Payment

class PaymentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('order', css_class='col-span-6'),
                Div('gateway', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('gateway_order_id', css_class='col-span-6'),
                Div('gateway_payment_id', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('method', css_class='col-span-6'),
                Div('status', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('amount', css_class='col-span-6'),
                Div('currency', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('authorized_at', css_class='col-span-6'),
                Div('captured_at', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('gateway_response', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('failure_reason', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Payment', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = Payment
        fields = (
            "order", "gateway_order_id", "gateway_payment_id", 
            "gateway", "method", "status", "amount", "currency", 
            "gateway_response", "failure_reason", "authorized_at", 
            "captured_at"
        )
        widgets = {
            "gateway_response": forms.Textarea(attrs={"rows": 3}), # JSON
            "failure_reason": forms.Textarea(attrs={"rows": 2}),
            "authorized_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "captured_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
