from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.catalog.models import ProductImage

class ProductImageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('product', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('image', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('alt_text', css_class='col-span-6'),
                Div('position', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('is_primary', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Image', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = ProductImage
        fields = ("product", "image", "alt_text", "position", "is_primary")
