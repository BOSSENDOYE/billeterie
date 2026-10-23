import base64
import hashlib
import hmac
import json
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TypeBillet(models.TextChoices):
    PREVENTE = 'prevente', 'Prévente'
    JOUR_J = 'jour_j', 'Jour J'


# Préfixe affiché devant le numéro : les deux séries de billets ne se confondent pas
PREFIXES = {TypeBillet.PREVENTE: 'PV', TypeBillet.JOUR_J: 'JJ'}


class Evenement(models.Model):
    artiste = models.CharField(max_length=120)
    titre = models.CharField(max_length=200)
    date = models.DateTimeField()
    lieu = models.CharField(max_length=200)
    ville = models.CharField(max_length=100)
    prix = models.PositiveIntegerField(help_text='Prix prévente, en FCFA')
    prix_jour_j = models.PositiveIntegerField(default=3000, help_text='Prix Jour J, en FCFA')
    quota_prevente = models.PositiveIntegerField(default=400)
    quota_jour_j = models.PositiveIntegerField(default=200)
    fin_prevente = models.DateTimeField(null=True, blank=True, help_text='Après cette date, la vente en ligne passe au tarif Jour J')
    capacite = models.PositiveIntegerField(default=600, help_text='Total des deux séries')
    image_url = models.CharField(max_length=300, blank=True, help_text='Ex : /artiste.jpeg')
    # Textes et couleur personnalisés du billet papier Jour J (vide = valeurs par défaut)
    design_papier = models.JSONField(default=dict, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'événement'

    def __str__(self):
        return self.titre

    def type_en_vente(self, maintenant=None):
        """Tarif appliqué à la vente : prévente jusqu'à fin_prevente, puis Jour J."""
        maintenant = maintenant or timezone.now()
        if self.fin_prevente and maintenant >= self.fin_prevente:
            return TypeBillet.JOUR_J
        return TypeBillet.PREVENTE

    def prix_de(self, type_billet):
        return self.prix_jour_j if type_billet == TypeBillet.JOUR_J else self.prix

    def quota_de(self, type_billet):
        return self.quota_jour_j if type_billet == TypeBillet.JOUR_J else self.quota_prevente


class Ticket(models.Model):
    class Statut(models.TextChoices):
        DISPONIBLE = 'disponible', 'Disponible'
        VENDU = 'vendu', 'Vendu'
        UTILISE = 'utilise', 'Utilisé'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evenement = models.ForeignKey(Evenement, on_delete=models.CASCADE, related_name='tickets')
    type = models.CharField(max_length=10, choices=TypeBillet.choices, default=TypeBillet.PREVENTE, db_index=True)
    numero = models.PositiveIntegerField()
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.DISPONIBLE, db_index=True)
    acheteur_nom = models.CharField(max_length=120, blank=True)
    acheteur_tel = models.CharField(max_length=20, blank=True)
    date_achat = models.DateTimeField(null=True, blank=True)
    date_scan = models.DateTimeField(null=True, blank=True)
    # Billet imprimé et vendu en papier (série Jour J) : valide dès son impression
    physique = models.BooleanField(default=False)

    class Meta:
        ordering = ['type', 'numero']
        constraints = [models.UniqueConstraint(fields=['evenement', 'type', 'numero'], name='ticket_type_numero_unique')]

    def __str__(self):
        return self.code

    @property
    def code(self):
        """Ex. « PV-042 » (prévente) ou « JJ-015 » (Jour J)."""
        return f'{PREFIXES[self.type]}-{self.numero:03d}'

    @property
    def prix(self):
        return self.evenement.prix_de(self.type)

    @property
    def signature(self):
        return signer(str(self.id))

    @property
    def qr_payload(self):
        # Format compact « B1.<uuid>.<signature> » (~40 caractères) : QR à gros modules,
        # lisible même affiché sur l'écran d'un autre téléphone
        return f'{QR_PREFIXE}{_b64(self.id.bytes)}.{signer_court(self.id)}'


def signer(ticket_id: str) -> str:
    """Signature HMAC-SHA256 tronquée : empêche de fabriquer un QR valide sans la clé serveur."""
    key = settings.TICKET_SIGNING_KEY.encode()
    return hmac.new(key, ticket_id.encode(), hashlib.sha256).hexdigest()[:20]


def signature_valide(ticket_id: str, sig: str) -> bool:
    return hmac.compare_digest(signer(ticket_id), sig or '')


QR_PREFIXE = 'B1.'


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def signer_court(ticket_id: uuid.UUID) -> str:
    """Signature HMAC-SHA256 tronquée à 80 bits, encodée en base64url (14 caractères)."""
    key = settings.TICKET_SIGNING_KEY.encode()
    return _b64(hmac.new(key, ticket_id.bytes, hashlib.sha256).digest()[:10])


def lire_qr(contenu: str):
    """Retourne l'identifiant du billet si le QR est authentique, sinon None.

    Accepte le format compact « B1.… » et l'ancien format JSON {"id", "sig"}.
    """
    contenu = (contenu or '').strip()
    if contenu.startswith(QR_PREFIXE):
        try:
            code_id, sig = contenu[len(QR_PREFIXE):].split('.')
            ticket_id = uuid.UUID(bytes=base64.urlsafe_b64decode(code_id + '=' * (-len(code_id) % 4)))
        except (ValueError, TypeError):
            return None
        return ticket_id if hmac.compare_digest(signer_court(ticket_id), sig) else None
    try:
        data = json.loads(contenu)
        ticket_id, sig = str(data['id']), str(data['sig'])
    except (ValueError, KeyError, TypeError):
        return None
    return ticket_id if signature_valide(ticket_id, sig) else None


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
    type = models.CharField(max_length=10, choices=TypeBillet.choices, default=TypeBillet.PREVENTE)
    canal = models.CharField(max_length=10, choices=[('en_ligne', 'En ligne'), ('guichet', 'Guichet')], default='en_ligne')
    nom = models.CharField(max_length=120)
    telephone = models.CharField(max_length=20)
    montant = models.PositiveIntegerField()
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE, db_index=True)
    # ID de transaction du reçu Wave, déclaré par l'acheteur ; unique pour empêcher sa réutilisation
    transaction_wave = models.CharField(max_length=60, unique=True, null=True, blank=True)
    declare_le = models.DateTimeField(null=True, blank=True)
    # Session Wave Checkout (paiement confirmé automatiquement par Wave) et son lien de paiement
    wave_session = models.CharField(max_length=60, unique=True, null=True, blank=True)
    wave_lien = models.CharField(max_length=300, blank=True)
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
