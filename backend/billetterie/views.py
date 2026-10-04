"""API JSON consommée par le frontend React."""
import hmac
import json
import re
from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import services
from .models import Paiement, Scan, Ticket, TypeBillet

TEL_RE = re.compile(r'^7[05678]\d{7}$')
# ID de transaction Wave : lettres, chiffres, tirets et underscores
TRANSACTION_RE = re.compile(r'^[A-Za-z0-9_-]{6,60}$')


# --- Helpers -----------------------------------------------------------------

def erreur(message, status=400):
    return JsonResponse({'erreur': message}, status=status)


def corps(request):
    try:
        return json.loads(request.body or b'{}')
    except ValueError:
        return {}


def staff_requis(view):
    """Protège les routes du personnel par un code d'accès (en-tête X-Staff-Code)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        code = request.headers.get('X-Staff-Code', '')
        if not hmac.compare_digest(code, settings.STAFF_ACCESS_CODE):
            return erreur('Accès réservé au personnel', 401)
        return view(request, *args, **kwargs)
    return csrf_exempt(wrapper)


def ser_evenement(ev):
    return {
        'id': ev.id,
        'artiste': ev.artiste,
        'titre': ev.titre,
        'date': ev.date.isoformat(),
        'lieu': ev.lieu,
        'ville': ev.ville,
        'prix': ev.prix,
        'prix_prevente': ev.prix,
        'prix_jour_j': ev.prix_jour_j,
        'quota_prevente': ev.quota_prevente,
        'quota_jour_j': ev.quota_jour_j,
        'fin_prevente': ev.fin_prevente.isoformat() if ev.fin_prevente else None,
        'capacite': ev.capacite,
        'image': ev.image_url,
    }


def ser_ticket(t, qr=False):
    data = {
        'id': str(t.id),
        'numero': t.numero,
        'type': t.type,
        'code': t.code,
        'prix': t.prix,
        'physique': t.physique,
        'statut': t.statut,
        'acheteur_nom': t.acheteur_nom or None,
        'acheteur_tel': t.acheteur_tel or None,
        'date_achat': t.date_achat.isoformat() if t.date_achat else None,
        'date_scan': t.date_scan.isoformat() if t.date_scan else None,
    }
    if qr:
        data['qr'] = t.qr_payload
    return data


def wave_url(montant):
    return f'{settings.WAVE_MERCHANT_URL}?{urlencode({"amount": montant})}'


def ser_paiement(p):
    return {
        'reference': p.reference,
        'nom': p.nom,
        'telephone': p.telephone,
        'montant': p.montant,
        'type': p.type,
        'canal': p.canal,
        'statut': p.statut,
        'transaction_wave': p.transaction_wave,
        'declare_le': p.declare_le.isoformat() if p.declare_le else None,
        'cree_le': p.cree_le.isoformat(),
        'ticket_id': str(p.ticket_id) if p.ticket_id else None,
        'wave_url': wave_url(p.montant),
        'simule': settings.PAIEMENT_SIMULE,
    }


def stats(ev):
    """Statistiques globales et par série (prévente / Jour J)."""
    par_type = {}
    for type_billet in TypeBillet.values:
        agg = ev.tickets.filter(type=type_billet).aggregate(
            vendus=Count('pk', filter=~Q(statut=Ticket.Statut.DISPONIBLE)),
            scannes=Count('pk', filter=Q(statut=Ticket.Statut.UTILISE)),
            physiques=Count('pk', filter=Q(physique=True)),
            physiques_entres=Count('pk', filter=Q(physique=True, statut=Ticket.Statut.UTILISE)),
        )
        quota = ev.quota_de(type_billet)
        prix = ev.prix_de(type_billet)
        encaisse = ev.paiements.filter(type=type_billet, statut=Paiement.Statut.REUSSI).aggregate(s=Sum('montant'))['s'] or 0
        par_type[type_billet] = {
            'total': quota,
            'vendus': agg['vendus'],
            'scannes': agg['scannes'],
            'restants': quota - agg['vendus'],
            'physiques': agg['physiques'],
            'prix': prix,
            # Paiements encaissés + billets papier présentés à l'entrée (vendus de la main à la main)
            'recette': encaisse + agg['physiques_entres'] * prix,
        }
    somme = lambda cle: sum(t[cle] for t in par_type.values())  # noqa: E731
    return {
        'total': somme('total'),
        'vendus': somme('vendus'),
        'scannes': somme('scannes'),
        'restants': somme('restants'),
        'recette': somme('recette'),
        'par_type': par_type,
    }


def tarif_en_vente(ev):
    type_billet = ev.type_en_vente()
    return {
        'type': type_billet,
        'prix': ev.prix_de(type_billet),
        'restants': stats(ev)['par_type'][type_billet]['restants'],
    }


def evenement_ou_404():
    ev = services.evenement_actif()
    if ev is None:
        return None, erreur('Aucun événement actif. Lancez : python manage.py seed_demo', 404)
    return ev, None


# --- Public ------------------------------------------------------------------

@require_GET
def evenement(request):
    ev, err = evenement_ou_404()
    if err:
        return err
    tarif = tarif_en_vente(ev)
    return JsonResponse({
        'evenement': ser_evenement(ev),
        'tarif': tarif,
        'restants': tarif['restants'],
        # En ligne : prévente uniquement. Les billets Jour J sont vendus en papier, sur place.
        'vente_en_ligne': tarif['type'] == TypeBillet.PREVENTE,
        'paiement_simule': settings.PAIEMENT_SIMULE,
    })


@csrf_exempt
@require_POST
def creer_paiement(request):
    ev, err = evenement_ou_404()
    if err:
        return err
    data = corps(request)
    nom = str(data.get('nom', '')).strip()
    tel = re.sub(r'\D', '', str(data.get('telephone', '')))
    if len(nom) < 2:
        return erreur('Nom invalide')
    if not TEL_RE.match(tel):
        return erreur('Numéro invalide : 9 chiffres commençant par 70, 75, 76, 77 ou 78')
    tarif = tarif_en_vente(ev)
    if tarif['type'] == TypeBillet.JOUR_J:
        return erreur(f"Prévente terminée : billets Jour J en vente sur place ({ev.prix_jour_j} FCFA)", 409)
    if tarif['restants'] == 0:
        message = ('Prévente épuisée : les billets Jour J seront en vente le jour du concert'
                   if tarif['type'] == TypeBillet.PREVENTE else 'Complet : tous les billets Jour J sont vendus')
        return erreur(message, 409)

    tel_fmt = f'{tel[:2]} {tel[2:5]} {tel[5:7]} {tel[7:]}'
    p = Paiement.objects.create(evenement=ev, nom=nom, telephone=tel_fmt, type=tarif['type'], montant=tarif['prix'])
    return JsonResponse({'paiement': ser_paiement(p), 'evenement': ser_evenement(ev)}, status=201)


@require_GET
def detail_paiement(request, reference):
    p = get_object_or_404(Paiement.objects.select_related('evenement'), reference=reference)
    return JsonResponse({'paiement': ser_paiement(p), 'evenement': ser_evenement(p.evenement)})


@csrf_exempt
@require_POST
def declarer_paiement(request, reference):
    """L'acheteur indique qu'il a payé sur Wave (l'ID de transaction est facultatif).

    Le lien marchand Wave ne notifie pas le site : le paiement passe « à vérifier »
    et un membre de l'équipe le confirme depuis le tableau de bord.
    """
    p = get_object_or_404(Paiement, reference=reference)
    if p.statut not in (Paiement.Statut.EN_ATTENTE, Paiement.Statut.A_VERIFIER):
        return erreur('Ce paiement a déjà été traité', 409)

    transaction = str(corps(request).get('transaction', '')).strip() or None
    if transaction:
        if not TRANSACTION_RE.match(transaction):
            return erreur("ID de transaction invalide : recopiez-le depuis votre reçu Wave")
        if Paiement.objects.filter(transaction_wave__iexact=transaction).exclude(pk=p.pk).exists():
            return erreur('Cet ID de transaction a déjà été utilisé', 409)

    p.transaction_wave = transaction
    p.declare_le = timezone.now()
    p.statut = Paiement.Statut.A_VERIFIER
    p.save(update_fields=['transaction_wave', 'declare_le', 'statut', 'maj_le'])
    return JsonResponse({'paiement': ser_paiement(p)})


@csrf_exempt
@require_POST
def simuler_paiement(request, reference):
    """Mode démonstration uniquement (PAIEMENT_SIMULE=1) : valide le paiement sans Wave."""
    if not settings.PAIEMENT_SIMULE:
        return erreur('Mode démonstration désactivé', 404)
    p = get_object_or_404(Paiement, reference=reference)
    if p.statut != Paiement.Statut.REUSSI:
        p = services.confirmer_paiement(p)
        if p.statut != Paiement.Statut.REUSSI:
            return erreur('Plus aucun billet disponible', 409)
    return JsonResponse({'paiement': ser_paiement(p)})


@require_GET
def detail_ticket(request, ticket_id):
    t = get_object_or_404(Ticket.objects.select_related('evenement'), pk=ticket_id)
    if t.statut == Ticket.Statut.DISPONIBLE:
        return erreur('Billet introuvable', 404)
    return JsonResponse({'ticket': ser_ticket(t, qr=True), 'evenement': ser_evenement(t.evenement)})


# --- Personnel ---------------------------------------------------------------

@staff_requis
@require_POST
def staff_login(request):
    return JsonResponse({'ok': True})


@staff_requis
@require_POST
def staff_scan(request):
    contenu = str(corps(request).get('qr', ''))
    r = services.scanner(contenu)
    out = {'resultat': r['resultat'], 'raison': r.get('raison')}
    if 'ticket' in r:
        out['ticket'] = ser_ticket(r['ticket'])
    return JsonResponse(out)


@staff_requis
@require_GET
def staff_scans(request):
    scans = Scan.objects.select_related('ticket__evenement')[:20]
    return JsonResponse({'scans': [
        {
            'id': s.id,
            'resultat': s.resultat,
            'raison': s.raison or None,
            'scanne_le': s.scanne_le.isoformat(),
            'nom': s.ticket.acheteur_nom if s.ticket else None,
            'numero': s.ticket.numero if s.ticket else None,
            'code': s.ticket.code if s.ticket else None,
            'type': s.ticket.type if s.ticket else None,
        }
        for s in scans
    ]})


@staff_requis
@require_GET
def staff_stats(request):
    ev, err = evenement_ou_404()
    if err:
        return err
    return JsonResponse({'evenement': ser_evenement(ev), 'stats': stats(ev)})


@staff_requis
@require_GET
def staff_tickets(request):
    ev, err = evenement_ou_404()
    if err:
        return err
    qs = ev.tickets.select_related('evenement')
    type_billet = request.GET.get('type', 'tous')
    if type_billet in TypeBillet.values:
        qs = qs.filter(type=type_billet)
    statut = request.GET.get('statut', 'tous')
    if statut == 'vendu':
        qs = qs.exclude(statut=Ticket.Statut.DISPONIBLE)
    elif statut in (Ticket.Statut.UTILISE, Ticket.Statut.DISPONIBLE):
        qs = qs.filter(statut=statut)
    q = request.GET.get('q', '').strip()
    if q:
        filtre = Q(acheteur_nom__icontains=q) | Q(acheteur_tel__icontains=q)
        if q.isdigit():
            filtre |= Q(numero=int(q))
        qs = qs.filter(filtre)
    # Activité la plus récente en premier, puis numéro
    qs = qs.order_by('-date_scan', '-date_achat', 'type', 'numero')
    return JsonResponse({'tickets': [ser_ticket(t) for t in qs]})


@staff_requis
@require_GET
def staff_paiements(request):
    statut = request.GET.get('statut', Paiement.Statut.A_VERIFIER)
    qs = Paiement.objects.select_related('ticket__evenement')
    if statut != 'tous':
        qs = qs.filter(statut=statut)
    qs = qs.order_by('declare_le', 'cree_le') if statut == Paiement.Statut.A_VERIFIER else qs.order_by('-maj_le')
    ser = []
    for p in qs[:100]:
        d = ser_paiement(p)
        d['numero'] = p.ticket.numero if p.ticket else None
        d['code'] = p.ticket.code if p.ticket else None
        ser.append(d)
    return JsonResponse({
        'paiements': ser,
        'a_verifier': Paiement.objects.filter(statut=Paiement.Statut.A_VERIFIER).count(),
    })


@staff_requis
@require_POST
def staff_valider_paiement(request, reference):
    p = get_object_or_404(Paiement, reference=reference)
    if p.statut == Paiement.Statut.REUSSI:
        return JsonResponse({'paiement': ser_paiement(p)})
    p = services.confirmer_paiement(p)
    if p.statut != Paiement.Statut.REUSSI:
        return erreur('Plus aucun billet disponible', 409)
    return JsonResponse({'paiement': ser_paiement(p)})


@staff_requis
@require_POST
def staff_rejeter_paiement(request, reference):
    p = get_object_or_404(Paiement, reference=reference)
    if p.statut == Paiement.Statut.REUSSI:
        return erreur('Paiement déjà confirmé : le billet a été émis', 409)
    p.statut = Paiement.Statut.ECHOUE
    p.save(update_fields=['statut', 'maj_le'])
    return JsonResponse({'paiement': ser_paiement(p)})


@staff_requis
@require_POST
def staff_vente_guichet(request):
    """Vente sur place : le billet est émis immédiatement (paiement encaissé par l'équipe)."""
    ev, err = evenement_ou_404()
    if err:
        return err
    data = corps(request)
    type_billet = data.get('type') or ev.type_en_vente()
    if type_billet not in TypeBillet.values:
        return erreur('Type de billet invalide')
    nom = str(data.get('nom', '')).strip()[:120]
    tel = re.sub(r'\D', '', str(data.get('telephone', '')))
    if tel and not TEL_RE.match(tel):
        return erreur('Numéro invalide : 9 chiffres commençant par 70, 75, 76, 77 ou 78')
    tel_fmt = f'{tel[:2]} {tel[2:5]} {tel[5:7]} {tel[7:]}' if tel else ''

    ticket = services.vendre_guichet(ev, type_billet, nom, tel_fmt, bool(data.get('entree_immediate', True)))
    if ticket is None:
        return erreur(f'Plus aucun billet {TypeBillet(type_billet).label} disponible', 409)
    return JsonResponse({'ticket': ser_ticket(ticket, qr=True), 'evenement': ser_evenement(ev)}, status=201)


@staff_requis
@require_POST
def staff_billets_physiques(request):
    """Émet les 200 billets Jour J en papier et renvoie le PDF à imprimer (10 par page A4)."""
    from .impression import generer_pdf

    ev, err = evenement_ou_404()
    if err:
        return err
    tickets = services.emettre_billets_physiques(ev)
    if not tickets:
        return erreur("Aucun billet Jour J disponible pour l'impression", 409)
    reponse = HttpResponse(generer_pdf(tickets, ev), content_type='application/pdf')
    reponse['Content-Disposition'] = 'attachment; filename="billets-jour-j.pdf"'
    return reponse
