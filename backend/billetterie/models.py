import hashlib
import hmac
import json
import secrets
import uuid

from django.conf import settings
from django.db import models


class Evenement(models.Model):
    artiste = models.CharField(max_length=120)
    titre = models.CharField(max_length=200)
    date = models.DateTimeField()
    lieu = models.CharField(max_length=200)
    ville = models.CharField(max_length=100)
    prix = models.PositiveIntegerField(help_text='En FCFA')
    capacite = models.PositiveIntegerField(default=300)
    image_url = models.CharField(max_length=300, blank=True, help_text='Ex : /artiste.jpeg')
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'événement'

    def __str__(self):
        return self.titre


class Ticket(models.Model):
    class Statut(models.TextChoices):
        DISPONIBLE = 'disponible', 'Disponible'
        VENDU = 'vendu', 'Vendu'
        UTILISE = 'utilise', 'Utilisé'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evenement = models.ForeignKey(Evenement, on_delete=models.CASCADE, related_name='tickets')
    numero = models.PositiveIntegerField()
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.DISPONIBLE, db_index=True)
    acheteur_nom = models.CharField(max_length=120, blank=True)
    acheteur_tel = models.CharField(max_length=20, blank=True)
    date_achat = models.DateTimeField(null=True, blank=True)
    date_scan = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['numero']
        constraints = [models.UniqueConstraint(fields=['evenement', 'numero'], name='ticket_numero_unique')]

    def __str__(self):
        return f'{self.numero:03d}/{self.evenement.capacite}'

    @property
    def signature(self):
        return signer(str(self.id))

    @property
    def qr_payload(self):
        return json.dumps({'id': str(self.id), 'sig': self.signature}, separators=(',', ':'))


def signer(ticket_id: str) -> str:
    """Signature HMAC-SHA256 tronquée : empêche de fabriquer un QR valide sans la clé serveur."""
    key = settings.TICKET_SIGNING_KEY.encode()
    return hmac.new(key, ticket_id.encode(), hashlib.sha256).hexdigest()[:20]


def signature_valide(ticket_id: str, sig: str) -> bool:
    return hmac.compare_digest(signer(ticket_id), sig or '')


def reference_paiement():
    return 'WV-' + secrets.token_hex(5).upper()


class Paiement(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente de paiement'
        A_VERIFIER = 'a_verifier', 'À vérifier'
        REUSSI = 'reussi', 'Confirmé'
        ECHOUE = 'echoue', 'Rejeté'

    reference = models.CharField(max_length=20, unique=True, default=reference_paiement, editable=False)
    evenement = models.ForeignKey(Evenement, on_delete=models.PROTECT, related_name='paiements')
    ticket = models.OneToOneField(Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiement')
    nom = models.CharField(max_length=120)
    telephone = models.CharField(max_length=20)
    montant = models.PositiveIntegerField()
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE, db_index=True)
    # ID de transaction du reçu Wave, déclaré par l'acheteur ; unique pour empêcher sa réutilisation
    transaction_wave = models.CharField(max_length=60, unique=True, null=True, blank=True)
    declare_le = models.DateTimeField(null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    maj_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-cree_le']

    def __str__(self):
        return self.reference


class Scan(models.Model):
    class Resultat(models.TextChoices):
        VALIDE = 'valide', 'Valide'
        UTILISE = 'utilise', 'Déjà utilisé'
        INVALIDE = 'invalide', 'Invalide'

    ticket = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name='scans')
    resultat = models.CharField(max_length=10, choices=Resultat.choices)
    raison = models.CharField(max_length=120, blank=True)
    scanne_le = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-scanne_le']
