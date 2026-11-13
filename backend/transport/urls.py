from django.urls import path

from .views import (
    admin_dashboard_stats,
    admin_enquiries_list,
    admin_enquiry_detail,
    admin_login,
    initiate_paystack_mpesa,
    paystack_webhook,
    public_enquiry_track,
    public_enquiry_create,
)

urlpatterns = [
    path("public/enquiries/", public_enquiry_create, name="public_enquiries_create"),
    path("public/track/<str:reference_number>/", public_enquiry_track, name="public_enquiry_track"),
    path("payments/paystack-stk/", initiate_paystack_mpesa, name="initiate_paystack_mpesa"),
    path("payments/paystack-webhook/", paystack_webhook, name="paystack_webhook"),
    path("admin/login/", admin_login, name="admin_login"),
    path("admin/enquiries/", admin_enquiries_list, name="admin_enquiries_list"),
    path("admin/enquiries/<uuid:enquiry_id>/", admin_enquiry_detail, name="admin_enquiry_detail"),
    path("admin/stats/", admin_dashboard_stats, name="admin_dashboard_stats"),
]