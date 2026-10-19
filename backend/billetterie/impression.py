"""PDF des billets papier (Jour J et Prévente) : 10 billets par page A4, avec traits de coupe.

Fond blanc pour l'impression ; chaque QR est signé par le serveur et ne sert qu'une fois.
"""
from io import BytesIO

import qrcode
from django.utils import timezone
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

NOIR = HexColor('#111111')
GRIS = HexColor('#666666')
COUPE = Color(0.6, 0.6, 0.6)

COLONNES, LIGNES = 2, 5
L_BILLET, H_BILLET = 95 * mm, 54 * mm
MARGE_X = (A4[0] - COLONNES * L_BILLET) / 2
MARGE_Y = (A4[1] - LIGNES * H_BILLET) / 2
BANDE = 9 * mm
QR = 29 * mm

MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
        'septembre', 'octobre', 'novembre', 'décembre']
JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']


def _date(ev):
    d = timezone.localtime(ev.date)
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year} · {d.hour}h{d.minute:02d}".replace('h00', 'h')


def _prix(montant):
    return f"{montant:,}".replace(',', ' ') + ' FCFA'


# --- Design personnalisable depuis le tableau de bord ---------------------------

CHAMPS_DESIGN = {
    # clé : (libellé, longueur max)
    'bandeau': ('Bandeau vertical', 12),
    'surtitre': ('Surtitre', 40),
    'titre': ('Titre (artiste)', 40),
    'date': ('Date et heure', 50),
    'lieu': ('Lieu', 90),
    'prix': ('Prix', 20),
    'mention': ('Mention en bas', 45),
    'couleur': ('Couleur principale', 7),
}


TYPES_PAPIER = ('jour_j', 'prevente')


def design_par_defaut(ev, type_billet='jour_j'):
    prevente = type_billet == 'prevente'
    return {
        'bandeau': 'PRÉVENTE' if prevente else 'JOUR J',
        'surtitre': 'BILLET  ·  PRÉVENTE' if prevente else 'BILLET  ·  JOUR J',
        'titre': ev.artiste.upper(),
        'date': _date(ev),
        'lieu': f'{ev.lieu} — {ev.ville}',
        'prix': _prix(ev.prix if prevente else ev.prix_jour_j),
        'mention': 'Un billet = une entrée',
        # Or foncé pour la prévente (lisible imprimé sur blanc), rubis pour le Jour J
        'couleur': '#A8862A' if prevente else '#C8102E',
    }


def design_enregistre(ev, type_billet):
    """Design personnalisé d'un type. Ancien format (dict à plat) = design Jour J."""
    stocke = ev.design_papier or {}
    if any(t in stocke for t in TYPES_PAPIER):
        return stocke.get(type_billet) or {}
    return stocke if type_billet == 'jour_j' else {}


def design_effectif(ev, type_billet='jour_j'):
    """Valeurs par défaut, remplacées par celles enregistrées (champs non vides)."""
    design = design_par_defaut(ev, type_billet)
    design.update({k: v for k, v in design_enregistre(ev, type_billet).items() if k in CHAMPS_DESIGN and v})
    return design


def _qr(c, valeur, x, y, cote):
    """QR vectoriel (net à toute taille) : une bande noire par suite de modules d'une ligne."""
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2)
    q.add_data(valeur)
    q.make(fit=True)
    matrice = q.get_matrix()
    module = cote / len(matrice)
    c.setFillColor(white)
    c.rect(x, y, cote, cote, stroke=0, fill=1)
    c.setFillColor(NOIR)
    for i, ligne in enumerate(matrice):
        ry = y + cote - (i + 1) * module
        j = 0
        while j < len(ligne):
            if ligne[j]:
                debut = j
                while j < len(ligne) and ligne[j]:
                    j += 1
                # léger chevauchement : pas de liseré blanc entre modules à l'impression
                c.rect(x + debut * module, ry, (j - debut) * module + 0.05, module + 0.05, stroke=0, fill=1)
            else:
                j += 1


def _billet(c, ticket, ev, x, y, design):
    accent = HexColor(design['couleur'])
    # Traits de coupe (pointillés gris)
    c.setStrokeColor(COUPE)
    c.setDash(2, 2)
    c.setLineWidth(0.4)
    c.rect(x, y, L_BILLET, H_BILLET)
    c.setDash()

    # Bande verticale « JOUR J »
    c.setFillColor(accent)
    c.rect(x, y, BANDE, H_BILLET, stroke=0, fill=1)
    c.saveState()
    c.translate(x + BANDE / 2 + 2.2 * mm, y + H_BILLET / 2)
    c.rotate(90)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(0, 0, ' '.join(design['bandeau'].upper()))
    c.restoreState()

    # Souche : QR + numéro, séparée par un pointillé
    souche_x = x + L_BILLET - QR - 6 * mm
    c.setStrokeColor(accent)
    c.setDash(1.5, 2)
    c.line(souche_x - 2 * mm, y + 4 * mm, souche_x - 2 * mm, y + H_BILLET - 4 * mm)
    c.setDash()
    _qr(c, ticket.qr_payload, souche_x + 1 * mm, y + 13 * mm, QR)
    c.setFillColor(NOIR)
    c.setFont('Helvetica', 6.5)
    c.drawCentredString(souche_x + 1 * mm + QR / 2, y + 9.5 * mm, 'BILLET N°')
    c.setFont('Helvetica-Bold', 12)
    c.setFillColor(accent)
    c.drawCentredString(souche_x + 1 * mm + QR / 2, y + 4.5 * mm, ticket.code)

    # Partie principale
    gx = x + BANDE + 4 * mm
    largeur = souche_x - 4 * mm - gx
    haut = y + H_BILLET - 7 * mm
    c.setFillColor(accent)
    c.setFont('Helvetica-Bold', 6.5)
    c.drawString(gx, haut, design['surtitre'])

    c.setFillColor(NOIR)
    c.setFont('Helvetica-Bold', 14)
    lignes = simpleSplit(design['titre'], 'Helvetica-Bold', 14, largeur)
    ty = haut - 7 * mm
    for ligne in lignes[:2]:
        c.drawString(gx, ty, ligne)
        ty -= 5.2 * mm

    c.setFont('Helvetica-Bold', 8)
    c.drawString(gx, ty, design['date'])
    ty -= 4 * mm
    c.setFillColor(GRIS)
    c.setFont('Helvetica', 7)
    for ligne in simpleSplit(design['lieu'], 'Helvetica', 7, largeur)[:2]:
        c.drawString(gx, ty, ligne)
        ty -= 3.3 * mm

    c.setFillColor(accent)
    c.setFont('Helvetica-Bold', 13)
    c.drawString(gx, y + 8 * mm, design['prix'])
    c.setFillColor(GRIS)
    c.setFont('Helvetica', 6)
    c.drawString(gx, y + 4.3 * mm, design['mention'])


def generer_pdf(tickets, ev, type_billet=None):
    """Retourne le PDF (bytes) des billets donnés (d'un même type), dans l'ordre."""
    type_billet = type_billet or (tickets[0].type if tickets else 'jour_j')
    tampon = BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    design = design_effectif(ev, type_billet)
    c.setTitle(f"Billets {'Prévente' if type_billet == 'prevente' else 'Jour J'} — {ev.artiste}")
    c.setAuthor('Guichet Billetterie')
    par_page = COLONNES * LIGNES
    for i, ticket in enumerate(tickets):
        if i and i % par_page == 0:
            c.showPage()
        rang = i % par_page
        col, lig = rang % COLONNES, rang // COLONNES
        _billet(c, ticket, ev, MARGE_X + col * L_BILLET, A4[1] - MARGE_Y - (lig + 1) * H_BILLET, design)
    c.save()
    return tampon.getvalue()
