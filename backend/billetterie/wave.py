"""API Wave Checkout : session de paiement par commande, confirmée par webhook signé.

Contrairement au lien marchand, Wave notifie le site à chaque paiement réussi :
le billet est émis sans intervention de l'équipe.
"""
import hashlib
import hmac
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

API_SESSIONS = 'https://api.wave.com/v1/checkout/sessions'


class WaveErreur(Exception):
    pass


def actif():
    return bool(settings.WAVE_API_KEY) and not settings.PAIEMENT_SIMULE


def _appel(url, corps=None):
    requete = Request(url, method='POST' if corps is not None else 'GET', headers={
        'Authorization': f'Bearer {settings.WAVE_API_KEY}',
        'Content-Type': 'application/json',
    }, data=json.dumps(corps).encode() if corps is not None else None)
    try:
        with urlopen(requete, timeout=15) as reponse:
            return json.loads(reponse.read())
    except HTTPError as e:
        raise WaveErreur(f'Wave a répondu {e.code} : {e.read()[:300]!r}') from e
    except (URLError, TimeoutError, ValueError) as e:
        raise WaveErreur(f'Wave injoignable : {e}') from e


def creer_session(paiement, url_retour):
    """Ouvre une session de paiement Wave au montant exact ; client_reference = notre référence."""
    return _appel(API_SESSIONS, {
        'amount': str(paiement.montant),
        'currency': 'XOF',
        'client_reference': paiement.reference,
        'success_url': url_retour,
        'error_url': url_retour,
    })


def lire_session(session_id):
    return _appel(f'{API_SESSIONS}/{session_id}')


def signature_valide(entete, corps: bytes) -> bool:
    """En-tête « Wave-Signature: t=<horodatage>,v1=<hmac>[,v1=…] » ; HMAC-SHA256 de horodatage + corps."""
    secret = settings.WAVE_WEBHOOK_SECRET
    if not secret or not entete:
        return False
    parties = [p.split('=', 1) for p in entete.split(',') if '=' in p]
    horodatage = next((v for k, v in parties if k.strip() == 't'), None)
    if horodatage is None:
        return False
    attendu = hmac.new(secret.encode(), horodatage.encode() + corps, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(attendu, v.strip()) for k, v in parties if k.strip() == 'v1')
