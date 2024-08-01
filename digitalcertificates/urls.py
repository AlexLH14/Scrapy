from django.urls import path

import digitalcertificates.views as views

app_name = 'digitalcertificates'

urlpatterns = [
    path('pin/eval/', views.CertificateScrapperPinAPIView.as_view(), name='pin_eval'),
    path('<uuid:certificate_order_id>/clavepin1/', views.clave_pin_landing1_view, name='clavepin1'),
    path('<uuid:certificate_order_id>/clavepin2/<request_type>', views.clave_pin_landing2_view, name='clavepin2'),
    path('<uuid:certificate_order_id>/clavepin3/<request_type>', views.clave_pin_landing3_view, name='clavepin3'),
    path('<uuid:certificate_order_id>/clavepin4/<request_type>', views.clave_pin_landing4_view, name='clavepin4'),
]
