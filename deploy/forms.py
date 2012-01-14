from django.forms import ModelForm
from django import forms

from deploy.models import Platform

class Migrate(forms.Form):
    new_platform = forms.ModelMultipleChoiceField( queryset=Platform.objects.all() )
    
