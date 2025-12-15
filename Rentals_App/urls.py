from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('queries/', views.query_page, name='queries'),
    path('add_rental/', views.add_rental, name='add_rental'),
    path('owner_search/', views.owner_search, name='owner_search'),
    path('owner_analysis/', views.owner_analysis, name='owner_analysis'),
]
