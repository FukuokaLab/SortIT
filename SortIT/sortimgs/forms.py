from django import forms
from .models import Image

# forms.py
class ImageForm(forms.ModelForm):

    image = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={"allow_multiple_selected": True}), required=False
    )
    class Meta:
        model = Image
        fields = ('image',)