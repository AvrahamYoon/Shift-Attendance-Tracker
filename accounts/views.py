from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

class AppLoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return resolve_post_login_url(self.request.user)


@login_required
def post_login_redirect(request):
    return redirect(resolve_post_login_url(request.user))


def resolve_post_login_url(user):
    if user.is_staff:
        return reverse("admin:index")
    return reverse("home")
