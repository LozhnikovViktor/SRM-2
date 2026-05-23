from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

app_name = 'tenders'
urlpatterns = [
    path('', views.TenderListView.as_view(), name='list'),
    path('add/', views.TenderCreateView.as_view(), name='add'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(template_name='tenders/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='tenders:list'), name='logout'),
    path('edit/<int:pk>/', views.TenderUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', views.TenderDeleteView.as_view(), name='delete'),
]