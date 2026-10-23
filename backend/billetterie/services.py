"""Logique métier : vente, contrôle d'accès, données de démo."""
import random
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from .models import Evenement, Paiement, Scan, Ticket, TypeBillet, lire_qr


def evenement_actif():
    return Evenement.objects.filter(actif=True).first()


@transaction.atomic
def confirmer_paiement(paiement: Paiement) -> Paiement:
    """Confirme le paiement et attribue le prochain billet libre de son type (verrou de ligne).

    Le type (prévente / Jour J) est celui du tarif payé, même si la validation a lieu plus tard.
    """
    paiement = Paiement.objects.select_for_update().get(pk=paiement.pk)
    if paiement.statut == Paiement.Statut.REUSSI:
        return paiement  # idempotent : une double validation ne vend pas deux billets

    ticket = (
        Ticket.objects.select_for_update()
        .filter(evenement=paiement.evenement, type=paiement.type, statut=Ticket.Statut.DISPONIBLE)
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


def appliquer_session_wave(session: dict):
    """Applique l'état d'une session Wave Checkout (webhook ou relecture) au paiement correspondant.

    Paiement réussi au bon montant : billet émis automatiquement. Si la série est épuisée,
    le paiement reste « à vérifier » pour que l'équipe le rembourse.
    Session expirée sans paiement : la commande est rejetée. Retourne le paiement, ou None.
    """
    p = Paiement.objects.filter(reference=session.get('client_reference') or '').first()
    if p is None or p.statut in (Paiement.Statut.REUSSI, Paiement.Statut.ECHOUE):
        return p

    if session.get('payment_status') == 'succeeded':
        if str(session.get('amount')) != str(p.montant) or session.get('currency') != 'XOF':
            return p  # montant inattendu : jamais de billet automatique
        transaction_id = session.get('transaction_id') or None
        if transaction_id and Paiement.objects.filter(transaction_wave=transaction_id).exclude(pk=p.pk).exists():
            return p
        p.transaction_wave = transaction_id
        p.declare_le = p.declare_le or timezone.now()
        p.statut = Paiement.Statut.A_VERIFIER
        p.save(update_fields=['transaction_wave', 'declare_le', 'statut', 'maj_le'])
        return confirmer_paiement(p)

    if session.get('checkout_status') == 'expired':
        p.statut = Paiement.Statut.ECHOUE
        p.save(update_fields=['statut', 'maj_le'])
    return p


@transaction.atomic
def vendre_guichet(ev, type_billet, nom='', telephone='', entree_immediate=True):
    """Vente sur place par l'équipe (paiement encaissé au guichet).

    Avec entree_immediate, le billet est directement marqué « utilisé » : l'acheteur entre tout de suite.
    Retourne le billet, ou None si la série est épuisée.
    """
    ticket = (
        Ticket.objects.select_for_update()
        .filter(evenement=ev, type=type_billet, statut=Ticket.Statut.DISPONIBLE)
        .order_by('numero')
        .first()
    )
    if ticket is None:
        return None

    maintenant = timezone.now()
    ticket.acheteur_nom = nom or 'Vente guichet'
    ticket.acheteur_tel = telephone
    ticket.date_achat = maintenant
    if entree_immediate:
        ticket.statut = Ticket.Statut.UTILISE
        ticket.date_scan = maintenant
    else:
        ticket.statut = Ticket.Statut.VENDU
    ticket.save()

    Paiement.objects.create(
        evenement=ev, ticket=ticket, type=type_billet, canal='guichet', nom=ticket.acheteur_nom,
        telephone=telephone, montant=ev.prix_de(type_billet), statut=Paiement.Statut.REUSSI,
    )
    if entree_immediate:
        Scan.objects.create(ticket=ticket, resultat=Scan.Resultat.VALIDE, raison='Vente guichet')
    return ticket


# Billets papier par défaut : tous les Jour J, 100 Prévente
PAPIER_PREVENTE_PAR_DEFAUT = 100


@transaction.atomic
def emettre_billets_physiques(ev, type_billet=TypeBillet.JOUR_J, nombre=None):
    """Émet des billets papier : ils deviennent valides (une seule entrée chacun).

    - Jour J : tous les billets disponibles de la série.
    - Prévente : jusqu'à `nombre` billets papier au total (100 par défaut), pris parmi les
      derniers numéros (PV-400, PV-399…) pour ne pas croiser la vente en ligne qui part de PV-001.
    Idempotent : les billets déjà émis ou vendus sont conservés.
    Retourne tous les billets papier du type, par numéro.
    """
    maintenant = timezone.now()
    disponibles = Ticket.objects.select_for_update().filter(evenement=ev, type=type_billet, statut=Ticket.Statut.DISPONIBLE)
    if type_billet == TypeBillet.PREVENTE:
        voulu = PAPIER_PREVENTE_PAR_DEFAUT if nombre is None else nombre
        deja = Ticket.objects.filter(evenement=ev, type=type_billet, physique=True).count()
        ids = list(disponibles.order_by('-numero').values_list('pk', flat=True)[:max(0, voulu - deja)])
        disponibles = Ticket.objects.filter(pk__in=ids)
    disponibles.update(statut=Ticket.Statut.VENDU, physique=True, acheteur_nom='Billet papier', date_achat=maintenant)
    return list(Ticket.objects.filter(evenement=ev, type=type_billet, physique=True).order_by('numero'))


@transaction.atomic
def reinitialiser_ticket(ticket):
    """Annule l'usage d'un billet (tests, erreur de manipulation).

    - Billet papier : il redevient valide (entrée annulée), il reste imprimé.
    - Autre billet : il redevient disponible à la vente ; son paiement est marqué rejeté et détaché.
    """
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    Scan.objects.filter(ticket=ticket).delete()
    if ticket.physique:
        ticket.statut = Ticket.Statut.VENDU
        ticket.date_scan = None
        ticket.save(update_fields=['statut', 'date_scan'])
        return ticket

    Paiement.objects.filter(ticket=ticket).update(ticket=None, statut=Paiement.Statut.ECHOUE)
    ticket.statut = Ticket.Statut.DISPONIBLE
    ticket.acheteur_nom = ''
    ticket.acheteur_tel = ''
    ticket.date_achat = None
    ticket.date_scan = None
    ticket.save()
    return ticket


def billets_jour_j_de_test(ev):
    """Billets Jour J à remettre à zéro : vendus hors papier, ou billets papier déjà scannés."""
    jour_j = Ticket.objects.filter(evenement=ev, type=TypeBillet.JOUR_J)
    return jour_j.filter(physique=False).exclude(statut=Ticket.Statut.DISPONIBLE) | jour_j.filter(
        physique=True, statut=Ticket.Statut.UTILISE
    )


def reinitialiser_tests_jour_j(ev):
    tickets = list(billets_jour_j_de_test(ev).order_by('numero'))
    for t in tickets:
        reinitialiser_ticket(t)
    return [t.code for t in tickets]


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
        date=datetime(2026, 12, 26, 19, 0, tzinfo=tz),
        lieu='Terrain de tennis de la Cité Mbaye Mbaye',
        ville='Mboro',
        prix=2500,
        prix_jour_j=3000,
        quota_prevente=400,
        quota_jour_j=200,
        capacite=600,
        # Prévente jusqu'à la veille 23h59, Jour J à partir du 26 décembre 00h00
        fin_prevente=datetime.combine(datetime(2026, 12, 26).date(), time(0, 0), tzinfo=tz),
        image_url='/artiste.jpeg',
    )
    Ticket.objects.bulk_create(
        Ticket(evenement=ev, type=type_billet, numero=n)
        for type_billet in (TypeBillet.PREVENTE, TypeBillet.JOUR_J)
        for n in range(1, ev.quota_de(type_billet) + 1)
    )

    rnd = random.Random(2026)
    now = timezone.now()
    for t in Ticket.objects.filter(evenement=ev, type=TypeBillet.PREVENTE, numero__lte=vendus):
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
