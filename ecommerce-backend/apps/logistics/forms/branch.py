from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.logistics.models import Branch

class BranchForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('hub', css_class='col-span-6'),
                Div('name', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('code', css_class='col-span-6'),
                Div('contact_phone', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('agent_capacity', css_class='col-span-6'),
                Div('is_active', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('address', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('service_pincodes', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Branch', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = Branch
        fields = (
            "hub", "name", "code", "address", "service_pincodes", 
            "contact_phone", "agent_capacity", "is_active"
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "service_pincodes": forms.Textarea(attrs={"rows": 2}), # JSON
        }
