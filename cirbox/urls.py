"""cirbox URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from cirbox.check import HealthView
from src.apps.certificate_order.certificate_views import CertificateOrderView

router = routers.DefaultRouter(trailing_slash=True)
router.register('certificateorder', CertificateOrderView, basename='CertificateOrderView')
router.register('processorder', CertificateOrderView, basename='ProcessOrderView')
router.register('health', HealthView, basename='HealthView')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('digitalcertificates/', include('digitalcertificates.urls')),
    path('', include(router.urls)),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
