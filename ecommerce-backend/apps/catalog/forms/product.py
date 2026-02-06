from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from apps.catalog.models import Product

class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('vendor', css_class='col-span-6'),
                Div('category', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('brand', css_class='col-span-6'),
                Div('name', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('slug', css_class='col-span-6'),
                Div('status', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
             Div(
                Div('published_at', css_class='col-span-6'),
                Div('is_featured', css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('short_description', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('description', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('specifications', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Div(
                Div('seo_data', css_class='col-span-12'),
                css_class='grid grid-cols-12 gap-4'
            ),
            Submit('submit', 'Save Product', css_class='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded')
        )

    class Meta:
        model = Product
        fields = (
            "vendor", "category", "brand", "name", "slug", 
            "short_description", "description", "specifications", 
            "status", "is_featured", "seo_data", "published_at"
        )
        widgets = {
            "short_description": forms.Textarea(attrs={"rows": 2}),
            "description": forms.Textarea(attrs={"rows": 5}),
            "specifications": forms.Textarea(attrs={"rows": 3}),
            "seo_data": forms.Textarea(attrs={"rows": 3}),
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
