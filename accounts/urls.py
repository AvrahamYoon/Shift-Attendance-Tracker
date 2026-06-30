from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.AppLoginView.as_view(), name="login"),
    path("post-login/", views.post_login_redirect, name="post_login"),
]
