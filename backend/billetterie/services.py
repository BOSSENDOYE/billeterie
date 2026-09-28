"""Logique métier : vente, contrôle d'accès, données de démo."""
import random
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .models import Evenement, Paiement, Scan, Ticket, lire_qr


def evenement_actif():
    return Evenement.objects.filter(actif=True).first()


@transaction.atomic
def confirmer_paiement(paiement: Paiement) -> Paiement:
    """Confirme le paiement (validé par l'équipe) et attribue le prochain billet libre (verrou de ligne)."""
    paiement = Paiement.objects.select_for_update().get(pk=paiement.pk)
    if paiement.statut == Paiement.Statut.REUSSI:
        return paiement  # idempotent : une double validation ne vend pas deux billets

    ticket = (
        Ticket.objects.select_for_update()
        .filter(evenement=paiement.evenement, statut=Ticket.Statut.DISPONIBLE)
        .order_by('numero')
        .first()
    )
    if ticket is None:
        return paiement  # complet : le paiement reste en l'état, à rembourser

    ticket.statut = Ticket.Statut.VENDU
    ticket.acheteur_nom = paiement.nom
    ticket.acheteur_tel = paiement.telephone
    ticket.date_achat = timezone.now()
    ticket.save()

    paiement.ticket = ticket
    paiement.statut = Paiement.Statut.REUSSI
    paiement.save(update_fields=['ticket', 'statut', 'maj_le'])
    return paiement


def _invalide(raison):
    Scan.objects.create(resultat=Scan.Resultat.INVALIDE, raison=raison)
    return {'resultat': 'invalide', 'raison': raison}


@transaction.atomic
def scanner(contenu: str) -> dict:
    """Vérifie un QR code et le consomme. Le verrou empêche deux entrées simultanées."""
    ticket_id = lire_qr(contenu)
    if ticket_id is None:
        return _invalide('QR code non reconnu ou falsifié')

    ticket = Ticket.objects.select_for_update().select_related('evenement').filter(pk=ticket_id).first()
    if ticket is None or ticket.statut == Ticket.Statut.DISPONIBLE:
        return _invalide('Billet non vendu')

    if ticket.statut == Ticket.Statut.UTILISE:
        Scan.objects.create(ticket=ticket, resultat=Scan.Resultat.UTILISE)
        return {'resultat': 'utilise', 'ticket': ticket}

    ticket.statut = Ticket.Statut.UTILISE
    ticket.date_scan = timezone.now()
    ticket.save(update_fields=['statut', 'date_scan'])
    Scan.objects.create(ticket=ticket, resultat=Scan.Resultat.VALIDE)
    return {'resultat': 'valide', 'ticket': ticket}


NOMS = [
    'Aminata Diop', 'Moussa Ndiaye', 'Fatou Sow', 'Ibrahima Fall', 'Awa Ba',
    'Cheikh Mbaye', 'Mariama Sarr', 'Ousmane Diallo', 'Khady Gueye', 'Mamadou Kane',
    'Ndeye Faye', 'Abdoulaye Cissé', 'Rokhaya Thiam', 'Babacar Seck', 'Coumba Niang',
]


@transaction.atomic
def generer_demo(vendus=0, scannes=0):
    """(Ré)initialise l'événement et ses billets. vendus/scannes > 0 : fausses ventes de test."""
    Scan.objects.all().delete()
    Paiement.objects.all().delete()
    Ticket.objects.all().delete()
    Evenement.objects.all().delete()

    tz = timezone.get_current_timezone()
    ev = Evenement.objects.create(
        artiste='Dip Doundou Guiss',
        titre='Dip Doundou Guiss — Live à Mboro',
        date=datetime(2026, 12, 26, 20, 0, tzinfo=tz),
        lieu='Terrain de tennis de la Cité Mbaye Mbaye',
        ville='Mboro',
        prix=2500,
        capacite=300,
        image_url='/artiste.jpeg',
    )
    Ticket.objects.bulk_create(Ticket(evenement=ev, numero=n) for n in range(1, ev.capacite + 1))

    rnd = random.Random(2026)
    now = timezone.now()
    for t in Ticket.objects.filter(evenement=ev, numero__lte=vendus):
        t.statut = Ticket.Statut.UTILISE if t.numero <= scannes else Ticket.Statut.VENDU
        t.acheteur_nom = NOMS[(t.numero - 1) % len(NOMS)]
        t.acheteur_tel = f'7{rnd.choice("7860")} {rnd.randint(100, 999)} {rnd.randint(10, 99)} {rnd.randint(10, 99)}'
        t.date_achat = now - timedelta(hours=(vendus - t.numero + 2) * 3)
        if t.statut == Ticket.Statut.UTILISE:
            t.date_scan = now - timedelta(minutes=(scannes - t.numero) * 7 + 3)
        t.save()
        Paiement.objects.create(
            evenement=ev, ticket=t, nom=t.acheteur_nom, telephone=t.acheteur_tel,
            montant=ev.prix, statut=Paiement.Statut.REUSSI,
        )
    return ev
