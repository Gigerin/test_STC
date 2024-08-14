from django import forms

class SSHConnectionForm(forms.Form):
    hostname = forms.CharField(label="Hostname", max_length=100)
    username = forms.CharField(label="Username", max_length=100)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    port = forms.IntegerField(label="Port", initial=22)
