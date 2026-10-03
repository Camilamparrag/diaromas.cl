"""Formularios del checkout."""

from django import forms

from .models import Pedido


class CheckoutForm(forms.ModelForm):
    """Datos de entrega y contacto para cerrar el pedido por WhatsApp."""

    class Meta:
        model = Pedido
        fields = (
            "cliente_nombre",
            "cliente_email",
            "cliente_telefono",
            "entrega",
            "direccion",
            "comuna",
            "region",
            "notas",
        )
        labels = {
            "cliente_nombre": "Nombre completo",
            "cliente_email": "Email",
            "cliente_telefono": "Teléfono / WhatsApp",
            "entrega": "Modalidad de entrega",
            "direccion": "Dirección",
            "comuna": "Comuna",
            "region": "Región",
            "notas": "Notas para el pedido (opcional)",
        }
        widgets = {
            "cliente_nombre": forms.TextInput(attrs={"placeholder": "María Pérez"}),
            "cliente_email": forms.EmailInput(attrs={"placeholder": "maria@email.cl"}),
            "cliente_telefono": forms.TextInput(
                attrs={"placeholder": "+56 9 1234 5678"}
            ),
            "direccion": forms.TextInput(attrs={"placeholder": "Calle, número, depto"}),
            "comuna": forms.TextInput(attrs={"placeholder": "Providencia"}),
            "region": forms.TextInput(attrs={"placeholder": "Metropolitana"}),
            "notas": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Ej: entregar antes de las 18:00, es para regalo",
                }
            ),
            "entrega": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop("usuario", None)
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault("class", "campo")
            if campo.required:
                campo.widget.attrs["required"] = "required"
        self.fields["cliente_email"].required = False

        # Precarga los datos del cliente registrado
        if self.usuario is not None and self.usuario.is_authenticated:
            perfil = getattr(self.usuario, "perfil", None)
            self.fields["cliente_nombre"].initial = (
                self.initial.get("cliente_nombre")
                or f"{self.usuario.first_name} {self.usuario.last_name}".strip()
                or self.usuario.get_username()
            )
            self.fields["cliente_email"].initial = self.initial.get(
                "cliente_email", self.usuario.email
            )
            if perfil:
                self.fields["cliente_telefono"].initial = self.initial.get(
                    "cliente_telefono", perfil.telefono
                )

    def clean(self):
        datos = super().clean()
        if datos.get("entrega") == Pedido.Entrega.ENVIO:
            if not datos.get("direccion"):
                self.add_error("direccion", "Indica la dirección para el envío.")
            if not datos.get("comuna"):
                self.add_error("comuna", "Indica la comuna para el envío.")
        return datos