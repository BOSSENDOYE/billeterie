from django.urls import path

from . import views

urlpatterns = [
    path('evenement', views.evenement),
    path('paiements', views.creer_paiement),
    path('paiements/<str:reference>', views.detail_paiement),
    path('paiements/<str:reference>/declarer', views.declarer_paiement),
    path('paiements/<str:reference>/simuler', views.simuler_paiement),
    path('tickets/<uuid:ticket_id>', views.detail_ticket),
    path('wave/webhook', views.wave_webhook),
    path('staff/login', views.staff_login),
    path('staff/scan', views.staff_scan),
    path('staff/scans', views.staff_scans),
    path('staff/stats', views.staff_stats),
    path('staff/tickets', views.staff_tickets),
    path('staff/paiements', views.staff_paiements),
    path('staff/vente-guichet', views.staff_vente_guichet),
    path('staff/billets-physiques', views.staff_billets_physiques),
    path('staff/billets-physiques/apercu', views.staff_apercu_papier),
    path('staff/billets-physiques/design', views.staff_design_papier),
    path('staff/billets-jour-j/reinitialiser-tests', views.staff_reinitialiser_tests_jour_j),
    path('staff/tickets/<uuid:ticket_id>/reinitialiser', views.staff_reinitialiser_ticket),
    path('staff/paiements/<str:reference>/valider', views.staff_valider_paiement),
    path('staff/paiements/<str:reference>/rejeter', views.staff_rejeter_paiement),
]
