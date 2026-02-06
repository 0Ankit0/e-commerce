from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.logistics.models import Hub

class HubForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('name', css_class='col-span-6'),
                Div('code', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('type', css_class='col-span-6'),
                Div('contact_phone', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('city', css_class='col-span-6'),
                Div('state', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('pincode', css_class='col-span-6'),
                Div('is_active', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('latitude', css_class='col-span-6'),
                Div('longitude', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('address', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Hub', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = Hub
        fields = (
            "name", "code", "type", "address", "city", 
            "state", "pincode", "latitude", "longitude", 
            "contact_phone", "is_active"
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
        }
