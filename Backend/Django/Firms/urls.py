from django.urls import path, re_path

from . import views


urlpatterns = [
    # path('', views_old.index2, name='index'),
    # # path('firm/<str:firm_name>/', views.firm_report, name='firm_report'),
    # path('call/', book_call),
    re_path(r'^firm-list/?$', views.firm_list),
    re_path(r'firm-list/firm/?$', views.firm_view),
    re_path(r'get-firm-list/?$', views.get_firm_list),
    re_path(r'get-firm-list/firm/?$', views.firm_graph_data),
    re_path(r'call/?$', views.book_call),
]
