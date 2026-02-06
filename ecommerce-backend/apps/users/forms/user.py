from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class UserForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div("email", css_class="col-span-12"), css_class="grid grid-cols-12 gap-4"),
            Div(
                Div("is_active", css_class="col-span-6"),
                Div("is_superuser", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Div(
                Div("is_confirmed", css_class="col-span-6"),
                Div("otp_enabled", css_class="col-span-6"),
                css_class="grid grid-cols-12 gap-4",
            ),
            Submit(
                "submit", "Save User", css_class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            ),
        )

    class Meta:
        model = User
        fields = ("email", "is_active", "is_superuser", "is_confirmed", "otp_enabled")
