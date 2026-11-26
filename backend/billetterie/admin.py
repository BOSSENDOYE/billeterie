from django.contrib import admin

from .models import Evenement, Paiement, Scan, Ticket
from .services import creer_billets_manquants


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    list_display = ('titre', 'date', 'ville', 'prix', 'prix_vip', 'prix_vvip', 'capacite', 'actif')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Quota augmenté (ex. VIP 100 → 150) : les billets supplémentaires sont créés
        creer_billets_manquants(obj)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('numero', 'evenement', 'statut', 'acheteur_nom', 'acheteur_tel', 'date_achat', 'date_scan')
    list_filter = ('statut', 'evenement')
    search_fields = ('acheteur_nom', 'acheteur_tel', 'id')
    readonly_fields = ('id',)


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'nom', 'telephone', 'montant', 'transaction_wave', 'statut', 'ticket', 'cree_le')
    list_filter = ('statut',)
    search_fields = ('reference', 'nom', 'telephone', 'transaction_wave')


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ('scanne_le', 'resultat', 'ticket', 'raison')
    list_filter = ('resultat',)
