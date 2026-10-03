"""Vistas de cuentas: registro, perfil y cierre de sesión."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import ProfileForm, RegistrationForm
from .models import Profile


class RegistroView(CreateView):
    """Alta de nuevas cuentas de cliente."""

    form_class = RegistrationForm
    template_name = "accounts/registro.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request,
            f"¡Bienvenid@ a Diaromas, {self.object.first_name or self.object.username}!",
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Revisa los datos del formulario para continuar.")
        return super().form_invalid(form)


@login_required
def perfil(request):
    """Muestra y actualiza los datos de contacto del cliente."""
    perfil_usuario, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=perfil_usuario)
        if form.is_valid():
            form.save()
            messages.success(request, "Tus datos fueron actualizados.")
            return redirect("accounts:perfil")
        messages.error(request, "No pudimos guardar los cambios.")
    else:
        form = ProfileForm(instance=perfil_usuario)

    return render(
        request,
        "accounts/perfil.html",
        {"form": form, "perfil": perfil_usuario},
    )


class EditarPerfilView(UpdateView):
    """Alias con clase del perfil (misma lógica que la vista anterior)."""

    form_class = ProfileForm
    template_name = "accounts/perfil.html"
    success_url = reverse_lazy("accounts:perfil")

    def get_object(self, queryset=None):
        perfil_usuario, _ = Profile.objects.get_or_create(user=self.request.user)
        return perfil_usuario