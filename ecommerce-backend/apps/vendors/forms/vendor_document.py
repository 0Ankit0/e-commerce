from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.vendors.models import VendorDocument

class VendorDocumentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('vendor', css_class='col-span-6'),
                Div('doc_type', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('doc_number', css_class='col-span-6'),
                Div('status', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('file', css_class='col-span-6'),
                Div('verified_at', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('remarks', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Document', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = VendorDocument
        fields = ("vendor", "doc_type", "doc_number", "file", "status", "remarks", "verified_at")
        widgets = {
            "remarks": forms.Textarea(attrs={"rows": 2}),
            "verified_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
