from django.urls import path
from . import views

urlpatterns = [
    path("", views.ssh_connect, name="ssh_connect"),
    path("get_output/", views.get_output, name="get_output"),
]
