from django.forms import ModelForm
from django import forms
from deploy.models import Platform

class Migrate(forms.Form):
    new_platform = forms.ModelChoiceField( queryset=Platform.objects.all(),
                                           #widget=Select(
                                           #attrs={'size':'1'}, choices=Platform.objects.all())
                                                  )

class Drush(forms.Form):
    drush_command = forms.CharField()

    
