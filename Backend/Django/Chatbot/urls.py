from django.urls import path, re_path
from . import views

urlpatterns = [
    re_path(r'^message/?$', views.message),
    re_path(r'^init_chat/?$', views.init_chat),
    re_path(r'^get_response/?$', views.get_response),
    re_path(r'^dynamic/hoodwinked?$', views.hoodwinked_dynamic_chatbot),
    
]
