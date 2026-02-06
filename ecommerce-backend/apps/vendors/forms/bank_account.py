from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from apps.vendors.models import BankAccount


class BankAccountForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div("vendor", css_class="col-span-6"),
                Div("account_name", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("account_number", css_class="col-span-6"),
                Div("ifsc_code", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("bank_name", css_class="col-span-6"),
                Div("verification_status", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(Div("is_primary", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Submit(
                "submit",
                "Save Bank Account",
                css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
            ),
        )

    class Meta:
        model = BankAccount
        fields = (
            "vendor",
            "account_name",
            "account_number",
            "ifsc_code",
            "bank_name",
            "is_primary",
            "verification_status",
        )
