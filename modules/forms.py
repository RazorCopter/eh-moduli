import re
from django import forms
from django.core.exceptions import ValidationError
from .models import Customer, FormTemplate, User


class CustomerForm(forms.ModelForm):
    """Django ModelForm for Customer management and validation."""
    portal_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        min_length=6,
        help_text="Lascia vuoto per mantenere la password attuale (minimo 6 caratteri)."
    )

    class Meta:
        model = Customer
        fields = [
            'code', 'first_name', 'last_name', 'email',
            'phone', 'nas_folder_name', 'notes', 'active'
        ]

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip()
        if not code:
            raise ValidationError("Il codice cliente è obbligatorio.")
        if not re.match(r'^[A-Za-z0-9_\-]+$', code):
            raise ValidationError("Il codice cliente può contenere solo lettere, numeri, trattini e underscore.")
        qs = Customer.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"Il codice cliente '{code}' è già utilizzato.")
        return code

    def clean_nas_folder_name(self):
        folder = self.cleaned_data.get('nas_folder_name', '').strip()
        if not folder:
            raise ValidationError("La cartella NAS è obbligatoria.")
        if not re.match(r'^[A-Za-z0-9_\-]+$', folder):
            raise ValidationError("La cartella NAS può contenere solo lettere, numeri, trattini e underscore.")
        qs = Customer.objects.filter(nas_folder_name__iexact=folder)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"La cartella NAS '{folder}' è già utilizzata da un altro cliente.")
        return folder

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise ValidationError("L'indirizzo email è obbligatorio.")
        return email


class FormAssignmentForm(forms.Form):
    """Form to validate assignment of FormTemplate to a Customer with a dedicated project folder."""
    template_id = forms.UUIDField(required=True)
    customer_id = forms.UUIDField(required=True)
    project_name = forms.CharField(max_length=200, required=True)
    access_password = forms.CharField(required=False, min_length=4)

    def clean_project_name(self):
        project = self.cleaned_data.get('project_name', '').strip()
        if not project:
            raise ValidationError("Il nome del progetto è obbligatorio.")
        if re.search(r'[\/\\:\*\?"<>\|]', project):
            raise ValidationError("Il nome del progetto non può contenere caratteri non validi per cartelle NAS.")
        return project

    def clean_template_id(self):
        tid = self.cleaned_data.get('template_id')
        try:
            template = FormTemplate.objects.get(id=tid)
            if template.status == 'archived':
                raise ValidationError("Non è possibile assegnare un modello archiviato.")
            return template
        except FormTemplate.DoesNotExist:
            raise ValidationError("Modello selezionato non valido.")

    def clean_customer_id(self):
        cid = self.cleaned_data.get('customer_id')
        try:
            customer = Customer.objects.get(id=cid)
            if not customer.active:
                raise ValidationError("Il cliente selezionato non è attivo.")
            return customer
        except Customer.DoesNotExist:
            raise ValidationError("Cliente selezionato non valido.")


class AdminUserForm(forms.ModelForm):
    """Form for administrative user creation and role assignment."""
    password = forms.CharField(required=False, min_length=8, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise ValidationError("L'username è obbligatorio.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"L'username '{username}' è già in uso.")
        return username
