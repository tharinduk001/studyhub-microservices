from django import forms
from . models import Room


class RoomForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(RoomForm, self).__init__(*args, **kwargs)

        self.fields['description'].widget.attrs.update({'placeholder':'First 300 Characters Will Display...'})

    class Meta:
        model = Room
        fields = ['name', 'description']
