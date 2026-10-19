"""PDF des billets papier : 10 billets par page A4.

Deux formats bien distincts :
- Jour J   : comme le billet de la plateforme (fond sombre, photo de l'artiste, rubis, souche QR).
- Prévente : format blanc, grande bande verticale dorée « PRÉVENTE », texte noir.
Chaque QR est signé par le serveur et ne sert qu'une fois.
"""
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import qrcode
from django.utils import timezone
from PIL import Image, ImageEnhance
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

PHOTO = Path(__file__).resolve().parent / 'ressources' / 'artiste.jpeg'

# Couleurs du site (src/index.css)
ENCRE = HexColor('#0A0A0B')
SURFACE = HexColor('#121214')
CREME = HexColor('#F4F1EA')
MUET = HexColor('#9A9AA3')
REPERE = Color(0.55, 0.55, 0.55)
COUPE = Color(0.6, 0.6, 0.6)
PALETTES = {
    'prevente': {'clair': '#F0D78C', 'base': '#D4AF37', 'fonce': '#8C6D1F', 'texte_bandeau': '#0A0A0B'},
    'jour_j': {'clair': '#FF8B94', 'base': '#E0314B', 'fonce': '#7A0F1F', 'texte_bandeau': '#FFFFFF'},
}

# Gabarit : 2 colonnes x 5 lignes, billets séparés de 3 mm (coupe nette sans liseré)
COLONNES, LIGNES = 2, 5
L_BILLET, H_BILLET = 93 * mm, 52 * mm
ESPACE = 3 * mm
MARGE_X = (A4[0] - COLONNES * L_BILLET - (COLONNES - 1) * ESPACE) / 2
MARGE_Y = (A4[1] - LIGNES * H_BILLET - (LIGNES - 1) * ESPACE) / 2
SOUCHE = 30 * mm
QR = 21 * mm
DPI_PHOTO = 300

# Format Prévente (blanc) : billets jointifs de 95 x 54 mm, traits de coupe en pointillés
L_CLASSIQUE, H_CLASSIQUE = 95 * mm, 54 * mm
BANDE = 9 * mm
QR_CLASSIQUE = 27 * mm
NOIR = HexColor('#111111')
GRIS = HexColor('#666666')
OR_IMPRESSION = '#A8862A'  # or foncé, lisible imprimé sur blanc

MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
        'septembre', 'octobre', 'novembre', 'décembre']
JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

MOIS_COURTS = ['JANV', 'FÉVR', 'MARS', 'AVR', 'MAI', 'JUIN', 'JUIL', 'AOÛT', 'SEPT', 'OCT', 'NOV', 'DÉC']


def _date(ev):
    d = timezone.localtime(ev.date)
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year} · {d.hour}h{d.minute:02d}".replace('h00', 'h')


def _prix(montant):
    return f"{montant:,}".replace(',', ' ') + ' FCFA'


# --- Design personnalisable depuis le tableau de bord ---------------------------

CHAMPS_DESIGN = {
    # clé : (libellé, longueur max)
    'bandeau': ('Bandeau de la souche', 12),
    'surtitre': ('Surtitre', 40),
    'titre': ('Titre (artiste)', 40),
    'lieu': ('Lieu', 90),
    'prix': ('Prix', 20),
    'mention': ('Mention sous le QR', 30),
    'couleur': ('Couleur principale', 7),
}

TYPES_PAPIER = ('jour_j', 'prevente')


def design_par_defaut(ev, type_billet='jour_j'):
    prevente = type_billet == 'prevente'
    return {
        'bandeau': 'PRÉVENTE' if prevente else 'JOUR J',
        'surtitre': 'BILLET  ·  PRÉVENTE' if prevente else 'E-BILLET  ·  JOUR J',
        'titre': ev.artiste,
        'lieu': f'{ev.lieu} — {ev.ville}',
        'prix': _prix(ev.prix if prevente else ev.prix_jour_j),
        'mention': 'Un billet = une entrée',
        'couleur': OR_IMPRESSION if prevente else PALETTES[type_billet]['base'],
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


def _palette(type_billet, design):
    """Dégradé du type ; une couleur personnalisée le remplace par une teinte unie."""
    p = dict(PALETTES[type_billet])
    personnalisee = design['couleur'].upper() != p['base'].upper()
    if personnalisee:
        p.update(clair=design['couleur'], base=design['couleur'], fonce=design['couleur'], texte_bandeau='#FFFFFF')
    return {k: HexColor(v) for k, v in p.items()}


# --- Photo de fond (comme sur la plateforme : assombrie vers la gauche et le bas) ---------

def _degrade(taille, valeurs, horizontal):
    """Masque 'L' : interpolation linéaire des valeurs (0-255) de gauche à droite ou de haut en bas."""
    n = taille[0] if horizontal else taille[1]
    ligne = []
    for i in range(n):
        t = i / max(n - 1, 1) * (len(valeurs) - 1)
        k = min(int(t), len(valeurs) - 2)
        ligne.append(round(valeurs[k] + (valeurs[k + 1] - valeurs[k]) * (t - k)))
    bande = Image.new('L', (n, 1) if horizontal else (1, n))
    bande.putdata(ligne)
    return bande.resize(taille)


@lru_cache(maxsize=4)
def _photo_fond(type_billet, largeur_px, hauteur_px):
    photo = Image.open(PHOTO).convert('RGB')
    echelle = max(largeur_px / photo.width, hauteur_px / photo.height)
    photo = photo.resize((round(photo.width * echelle), round(photo.height * echelle)), Image.LANCZOS)
    # Visage (≈ 44 % de la largeur de la photo) placé aux deux tiers droits, comme sur le billet en ligne
    gauche = int(min(max(0.44 * photo.width - 0.66 * largeur_px, 0), photo.width - largeur_px))
    photo = photo.crop((gauche, 0, gauche + largeur_px, hauteur_px))
    photo = ImageEnhance.Brightness(ImageEnhance.Contrast(photo).enhance(1.08)).enhance(1.15)

    encre = Image.new('RGB', photo.size, (10, 10, 11))
    # Gauche → droite : encre 100 % → 80 % → 20 %  (from-ink via-ink/80 to-ink/20)
    photo = Image.composite(encre, photo, _degrade(photo.size, (245, 175, 25), horizontal=True))
    # Bas → haut : encre 90 % en bas, rien au-dessus de la moitié  (from-ink/90 via-transparent)
    photo = Image.composite(encre, photo, _degrade(photo.size, (0, 0, 215), horizontal=False))
    if type_billet == 'jour_j':  # teinte rubis du billet Jour J en ligne
        photo = Image.blend(photo, Image.new('RGB', photo.size, (122, 15, 31)), 0.14)
    tampon = BytesIO()
    photo.save(tampon, 'JPEG', quality=88)
    tampon.seek(0)
    return ImageReader(tampon)


# --- Dessin --------------------------------------------------------------------

def _texte_degrade(c, x, y, texte, police, taille, pal):
    """Texte rempli d'un dégradé vertical clair → foncé (text-gradient du site)."""
    c.saveState()
    t = c.beginText(x, y)
    t.setFont(police, taille)
    t.setTextRenderMode(7)  # le texte devient la zone de dessin
    t.textOut(texte)
    c.drawText(t)
    c.linearGradient(x, y + taille * 0.85, x, y - taille * 0.2, (pal['clair'], pal['base'], pal['fonce']), extend=True)
    c.restoreState()


def _qr(c, valeur, x, y, cote):
    """QR vectoriel sur carré blanc (zone de silence incluse)."""
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2)
    q.add_data(valeur)
    q.make(fit=True)
    matrice = q.get_matrix()
    module = cote / len(matrice)
    c.setFillColor(white)
    c.roundRect(x - 1.2 * mm, y - 1.2 * mm, cote + 2.4 * mm, cote + 2.4 * mm, 1.5 * mm, stroke=0, fill=1)
    c.setFillColor(ENCRE)
    for i, ligne in enumerate(matrice):
        ry = y + cote - (i + 1) * module
        j = 0
        while j < len(ligne):
            if ligne[j]:
                debut = j
                while j < len(ligne) and ligne[j]:
                    j += 1
                c.rect(x + debut * module, ry, (j - debut) * module + 0.05, module + 0.05, stroke=0, fill=1)
            else:
                j += 1


def _reperes(c, x, y):
    """Petits repères de coupe aux coins, dans l'espace blanc entre les billets."""
    c.setStrokeColor(REPERE)
    c.setLineWidth(0.3)
    long_ = 2 * mm
    for cx, cy, dx, dy in ((x, y, -1, -1), (x + L_BILLET, y, 1, -1), (x, y + H_BILLET, -1, 1), (x + L_BILLET, y + H_BILLET, 1, 1)):
        c.line(cx + dx * 0.6 * mm, cy, cx + dx * (0.6 * mm + long_), cy)
        c.line(cx, cy + dy * 0.6 * mm, cx, cy + dy * (0.6 * mm + long_))


def _billet(c, ticket, ev, x, y, design, type_billet):
    pal = _palette(type_billet, design)
    principal = L_BILLET - SOUCHE
    _reperes(c, x, y)

    # Fond sombre + photo (partie principale)
    c.setFillColor(ENCRE)
    c.rect(x, y, L_BILLET, H_BILLET, stroke=0, fill=1)
    largeur_px = round(principal / mm / 25.4 * DPI_PHOTO)
    hauteur_px = round(H_BILLET / mm / 25.4 * DPI_PHOTO)
    c.drawImage(_photo_fond(type_billet, largeur_px, hauteur_px), x, y, principal, H_BILLET)

    # Textes de la partie principale
    gx = x + 4.5 * mm
    largeur = principal - 8 * mm
    c.setFillColor(pal['base'])
    c.setFont('Helvetica-Bold', 5.6)
    c.drawString(gx, y + H_BILLET - 6.5 * mm, design['surtitre'].upper())

    titre = design['titre']
    taille = 17
    while taille > 9 and c.stringWidth(titre, 'Times-Bold', taille) > largeur:
        taille -= 0.5
    _texte_degrade(c, gx, y + H_BILLET - 14.5 * mm, titre, 'Times-Bold', taille, pal)

    c.setFillColor(Color(0.96, 0.95, 0.92, alpha=0.78))
    c.setFont('Helvetica', 6.2)
    ty = y + H_BILLET - 19.5 * mm
    for ligne in simpleSplit(design['lieu'], 'Helvetica', 6.2, largeur)[:2]:
        c.drawString(gx, ty, ligne)
        ty -= 2.8 * mm

    # Bloc date
    d = timezone.localtime(ev.date)
    bx, by, bw, bh = gx, y + 4.5 * mm, 12 * mm, 13.5 * mm
    c.setFillColor(Color(0.04, 0.04, 0.045, alpha=0.6))
    c.setStrokeColor(pal['base'])
    c.setLineWidth(0.6)
    c.roundRect(bx, by, bw, bh, 1.6 * mm, stroke=1, fill=1)
    c.setFillColor(pal['clair'])
    c.setFont('Times-Bold', 15)
    c.drawCentredString(bx + bw / 2, by + 6.3 * mm, f'{d.day:02d}')
    c.setFillColor(CREME)
    c.setFont('Helvetica-Bold', 5.6)
    c.drawCentredString(bx + bw / 2, by + 3.4 * mm, MOIS_COURTS[d.month - 1])
    c.setFillColor(MUET)
    c.setFont('Helvetica', 5)
    c.drawCentredString(bx + bw / 2, by + 1.2 * mm, str(d.year))

    # Heure et prix
    for i, (etiquette, valeur) in enumerate((('HEURE', f'{d.hour}h{d.minute:02d}'), ('PRIX', design['prix']))):
        fx = bx + bw + 3.5 * mm + i * 15 * mm
        c.setFillColor(pal['clair'])
        c.setFont('Helvetica-Bold', 5)
        c.drawString(fx, by + 9.2 * mm, etiquette)
        c.setFillColor(CREME)
        c.setFont('Helvetica-Bold', 7.2)
        c.drawString(fx, by + 5.6 * mm, valeur)

    # Souche
    sx = x + principal
    c.setFillColor(SURFACE)
    c.rect(sx, y, SOUCHE, H_BILLET, stroke=0, fill=1)
    hb = 6.2 * mm
    c.saveState()
    chemin = c.beginPath()
    chemin.rect(sx, y + H_BILLET - hb, SOUCHE, hb)
    c.clipPath(chemin, stroke=0, fill=0)
    c.linearGradient(sx, y + H_BILLET, sx + SOUCHE, y + H_BILLET - hb, (pal['clair'], pal['base'], pal['fonce']), extend=True)
    c.restoreState()
    c.setFillColor(pal['texte_bandeau'])
    c.setFont('Helvetica-Bold', 8.5)
    c.drawCentredString(sx + SOUCHE / 2, y + H_BILLET - hb + 2.1 * mm, ' '.join(design['bandeau'].upper()))

    centre = sx + SOUCHE / 2
    c.setFillColor(MUET)
    c.setFont('Helvetica', 4.8)
    c.drawCentredString(centre, y + H_BILLET - 10.6 * mm, 'BILLET N°')
    c.setFillColor(pal['clair'])
    c.setFont('Courier-Bold', 10)
    c.drawCentredString(centre, y + H_BILLET - 14.4 * mm, ticket.code)
    _qr(c, ticket.qr_payload, centre - QR / 2, y + 6.6 * mm, QR)
    c.setFillColor(MUET)
    c.setFont('Helvetica', 4.6)
    c.drawCentredString(centre, y + 2.4 * mm, design['mention'])

    # Perforation + encoches (comme le billet en ligne), puis cadre fin aux couleurs du type
    c.setStrokeColor(pal['base'])
    c.setLineWidth(0.5)
    c.setDash(1.4, 1.6)
    c.line(sx, y + 4 * mm, sx, y + H_BILLET - 4 * mm)
    c.setDash()
    c.setStrokeColor(pal['base'])
    c.setLineWidth(0.8)
    c.rect(x + 0.4, y + 0.4, L_BILLET - 0.8, H_BILLET - 0.8, stroke=1, fill=0)
    c.setFillColor(white)
    for cy in (y, y + H_BILLET):
        c.circle(sx, cy, 2.2 * mm, stroke=0, fill=1)
        c.setLineWidth(0.6)
        c.circle(sx, cy, 2.2 * mm, stroke=1, fill=0)


def _billet_classique(c, ticket, ev, x, y, design):
    """Format Prévente : fond blanc, bande verticale de couleur, texte noir, souche QR."""
    accent = HexColor(design['couleur'])
    # Traits de coupe (pointillés gris)
    c.setStrokeColor(COUPE)
    c.setDash(2, 2)
    c.setLineWidth(0.4)
    c.rect(x, y, L_CLASSIQUE, H_CLASSIQUE)
    c.setDash()

    # Bande verticale « PRÉVENTE »
    c.setFillColor(accent)
    c.rect(x, y, BANDE, H_CLASSIQUE, stroke=0, fill=1)
    c.saveState()
    c.translate(x + BANDE / 2 + 2.2 * mm, y + H_CLASSIQUE / 2)
    c.rotate(90)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 12)
    c.drawCentredString(0, 0, ' '.join(design['bandeau'].upper()))
    c.restoreState()

    # Souche : QR + numéro, séparée par un pointillé
    souche_x = x + L_CLASSIQUE - QR_CLASSIQUE - 6 * mm
    c.setStrokeColor(accent)
    c.setDash(1.5, 2)
    c.line(souche_x - 2 * mm, y + 4 * mm, souche_x - 2 * mm, y + H_CLASSIQUE - 4 * mm)
    c.setDash()
    _qr(c, ticket.qr_payload, souche_x + 2 * mm, y + 14 * mm, QR_CLASSIQUE)
    c.setFillColor(NOIR)
    c.setFont('Helvetica', 6.5)
    c.drawCentredString(souche_x + 2 * mm + QR_CLASSIQUE / 2, y + 9.5 * mm, 'BILLET N°')
    c.setFont('Helvetica-Bold', 12)
    c.setFillColor(accent)
    c.drawCentredString(souche_x + 2 * mm + QR_CLASSIQUE / 2, y + 4.5 * mm, ticket.code)

    # Partie principale
    gx = x + BANDE + 4 * mm
    largeur = souche_x - 4 * mm - gx
    haut = y + H_CLASSIQUE - 7 * mm
    c.setFillColor(accent)
    c.setFont('Helvetica-Bold', 6.5)
    c.drawString(gx, haut, design['surtitre'].upper())

    c.setFillColor(NOIR)
    c.setFont('Helvetica-Bold', 14)
    ty = haut - 7 * mm
    for ligne in simpleSplit(design['titre'].upper(), 'Helvetica-Bold', 14, largeur)[:2]:
        c.drawString(gx, ty, ligne)
        ty -= 5.2 * mm

    c.setFont('Helvetica-Bold', 8)
    c.drawString(gx, ty, _date(ev))
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
    if type_billet == 'prevente':
        # Format blanc : billets jointifs
        largeur, hauteur, espace, dessiner = L_CLASSIQUE, H_CLASSIQUE, 0, (
            lambda t, x, y: _billet_classique(c, t, ev, x, y, design))
    else:
        # Format plateforme : billets séparés de 3 mm
        largeur, hauteur, espace, dessiner = L_BILLET, H_BILLET, ESPACE, (
            lambda t, x, y: _billet(c, t, ev, x, y, design, type_billet))
    marge_x = (A4[0] - COLONNES * largeur - (COLONNES - 1) * espace) / 2
    marge_y = (A4[1] - LIGNES * hauteur - (LIGNES - 1) * espace) / 2
    par_page = COLONNES * LIGNES
    for i, ticket in enumerate(tickets):
        if i and i % par_page == 0:
            c.showPage()
        rang = i % par_page
        col, lig = rang % COLONNES, rang // COLONNES
        dessiner(ticket, marge_x + col * (largeur + espace), A4[1] - marge_y - (lig + 1) * hauteur - lig * espace)
    c.save()
    return tampon.getvalue()
