from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.payments.models import Refund

class RefundForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('payment', css_class='col-span-6'),
                Div('gateway_refund_id', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('amount', css_class='col-span-6'),
                Div('status', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('method', css_class='col-span-6'),
                Div('processed_at', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('reason', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('gateway_response', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Refund', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = Refund
        fields = (
            "payment", "gateway_refund_id", "amount", "reason", 
            "status", "method", "gateway_response", "processed_at"
        )
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 2}),
            "gateway_response": forms.Textarea(attrs={"rows": 3}), # JSON
            "processed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
