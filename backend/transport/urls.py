from django.urls import path

from .views import (
    admin_dashboard_stats,
    admin_enquiries_list,
    admin_enquiry_detail,
    admin_login,
    initiate_paystack_mpesa,
    verify_paystack_payment,
    paystack_webhook,
    admin_sms_settings,
    public_enquiry_track,
    public_enquiry_create,
)

urlpatterns = [
    path("public/enquiries/", public_enquiry_create, name="public_enquiries_create"),
    path("public/track/<str:reference_number>/", public_enquiry_track, name="public_enquiry_track"),
    path("payments/paystack-stk/", initiate_paystack_mpesa, name="initiate_paystack_mpesa"),
    path("payments/paystack-verify/", verify_paystack_payment, name="verify_paystack_payment"),
    path("payments/paystack-webhook/", paystack_webhook, name="paystack_webhook"),
    path("admin/login/", admin_login, name="admin_login"),
    path("admin/enquiries/", admin_enquiries_list, name="admin_enquiries_list"),
    path("admin/enquiries/<uuid:enquiry_id>/", admin_enquiry_detail, name="admin_enquiry_detail"),
    path("admin/stats/", admin_dashboard_stats, name="admin_dashboard_stats"),
    path("admin/sms-settings/", admin_sms_settings, name="admin_sms_settings"),
]