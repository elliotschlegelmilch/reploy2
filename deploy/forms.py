from django.forms import ModelForm
from django import forms
from deploy.models import Platform

class Migrate(forms.Form):
    new_platform = forms.ModelChoiceField( queryset=Platform.objects.all(),
                                           #widget=Select(
                                           #attrs={'size':'1'}, choices=Platform.objects.all())
                                                  )

class Clone(forms.Form):
    new_name = forms.CharField(required=True, label="Short Name")
    clone    = forms.BooleanField(required=False, label="Clone")


class Drush(forms.Form):
    drush_command = forms.CharField()

    
