"""Formularios de cuentas: registro y edición de perfil."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile

User = get_user_model()


class RegistrationForm(UserCreationForm):
    """Formulario de registro: nombre, apellido, email y teléfono opcional."""

    first_name = forms.CharField(
        label="Nombre", max_length=150, required=True, widget=forms.TextInput()
    )
    last_name = forms.CharField(
        label="Apellido", max_length=150, required=True, widget=forms.TextInput()
    )
    email = forms.EmailField(
        label="Email",
        required=True,
        help_text="Lo usamos solo para confirmar tus pedidos.",
    )
    telefono = forms.CharField(
        label="Teléfono / WhatsApp",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "+56 9 1234 5678"}),
    )
    acepta_terminos = forms.BooleanField(
        label="Acepto los términos y condiciones de la tienda",
        required=True,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["username"].help_text = (
            "Solo para tu acceso a la tienda. También puedes usar tu email."
        )
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Repite la contraseña"

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese email.")
        return email

    def clean_acepta_terminos(self):
        aceptado = self.cleaned_data.get("acepta_terminos")
        if not aceptado:
            raise forms.ValidationError("Debes aceptar los términos para crear la cuenta.")
        return aceptado

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.email = self.cleaned_data["email"]
        if commit:
            usuario.save()
            # El perfil lo crea la señal post_save; actualizamos el teléfono.
            perfil, _ = Profile.objects.get_or_create(user=usuario)
            perfil.telefono = self.cleaned_data.get("telefono", "")
            perfil.save()
        return usuario


class ProfileForm(forms.ModelForm):
    """Edición de los datos de contacto del cliente."""

    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150)
    email = forms.EmailField(label="Email")

    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "email", "telefono", "aromas_favoritos", "recibe_novedades")
        labels = {
            "telefono": "Teléfono / WhatsApp",
            "aromas_favoritos": "Aromas favoritos",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            usuario = self.instance.user
            self.fields["first_name"].initial = usuario.first_name
            self.fields["last_name"].initial = usuario.last_name
            self.fields["email"].initial = usuario.email

    def save(self, commit=True):
        perfil = super().save(commit=False)
        usuario = perfil.user
        usuario.first_name = self.cleaned_data["first_name"]
        usuario.last_name = self.cleaned_data["last_name"]
        nuevo_email = self.cleaned_data["email"]
        if nuevo_email and usuario.email != nuevo_email:
            existe = (
                type(usuario)
                .objects.filter(email__iexact=nuevo_email)
                .exclude(pk=usuario.pk)
                .exists()
            )
            if existe:
                raise forms.ValidationError({"email": "Ese email ya está en uso."})
            usuario.email = nuevo_email
        if commit:
            usuario.save()
            perfil.save()
        return perfil