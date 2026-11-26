"""Affiches et flyer « photo plein cadre » (300 dpi) — Dip Doundou Guiss, Mboro — CJICS présente.

Génère :
    public/affiche.jpg         A3 paysage (42 x 29,7 cm)  — servie sur le site (/affiche.jpg)
    public/affiche-40x30.jpg   40 x 30 cm paysage
    public/flyer-a5.jpg        flyer A5 portrait (14,8 x 21 cm)

Usage (depuis la racine du projet, sous Windows pour les polices) :
    pip install qrcode pillow numpy
    python outils/generer_affiche.py
"""
from pathlib import Path

import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

PROJET = Path(__file__).resolve().parent.parent
URL = 'https://billeteriecjics.com'
SITE = 'billeteriecjics.com'
ORGANISATEUR = 'CJICS'
INVITE = 'DJ DANY'  # artiste invité, affiché « avec DJ DANY » sous le nom
INFOLINE = ['+221 71 161 95 47', '+221 77 370 91 07', '+221 78 602 95 98']

DPI = 300
FORMATS = {
    'affiche.jpg': (420, 297),        # A3 paysage, en mm
    'affiche-40x30.jpg': (400, 300),  # 40 x 30 cm paysage
}

NOIR = (8, 8, 9)
OR_CLAIR, OR, OR_FONCE = (246, 222, 150), (212, 175, 55), (140, 109, 31)
CREME = (246, 242, 234)
GRIS = (190, 186, 178)
RUBIS = (232, 62, 86)
PLATINE = (214, 222, 236)

# (libellé, couleur du libellé, prix, couleur du prix)
TARIFS = [
    ('PRÉVENTE', OR, '2 500 FCFA', OR_CLAIR),
    ('JOUR J', RUBIS, '3 000 FCFA', CREME),
    ('VIP', OR_CLAIR, '10 000 FCFA', OR_CLAIR),
    ('VVIP', PLATINE, '25 000 FCFA', CREME),
]


def grille_tarifs(d, x, y, largeur, u, t_etiq, t_prix, pas):
    """Tarifs en 2 colonnes x 2 lignes : libellé au-dessus, prix en dessous. Retourne le bas."""
    col = largeur / 2
    f_prix = bahn(t_prix, 'Bold')
    for _, _, prix, _ in TARIFS:  # même taille de prix partout, ajustée à la colonne
        f_prix = min(f_prix, taille_ajustee(prix, lambda t: bahn(t, 'Bold'), t_prix, col - 1.5 * u), key=lambda f: f.size)
    for i, (etiquette, couleur, prix, couleur_prix) in enumerate(TARIFS):
        cx, cy = x + (i % 2) * col, y + (i // 2) * pas
        texte(d, cx, cy, etiquette, bahn(t_etiq, 'Bold'), couleur, lettrage=0.25 * u)
        d.text((cx, cy + t_etiq * 1.15), prix, font=f_prix, fill=couleur_prix)
    return y + 2 * pas

FONTS = 'C:/Windows/Fonts/'


def bahn(taille, style):
    f = ImageFont.truetype(FONTS + 'bahnschrift.ttf', int(taille))
    f.set_variation_by_name(style)
    return f


def serif(taille):
    return ImageFont.truetype(FONTS + 'georgiab.ttf', int(taille))


def taille_ajustee(texte, fabrique, taille_max, largeur_max):
    """Plus grande taille (<= taille_max) pour laquelle le texte tient dans largeur_max."""
    taille = taille_max
    mesure = ImageDraw.Draw(Image.new('L', (1, 1)))
    while taille > 10 and mesure.textlength(texte, font=fabrique(taille)) > largeur_max:
        taille *= 0.97
    return fabrique(taille)


def degrade_vertical(w, h, couleurs):
    colonne = Image.new('RGB', (1, h))
    px = colonne.load()
    n = len(couleurs) - 1
    for y in range(h):
        t = y / max(h - 1, 1) * n
        i = min(int(t), n - 1)
        f = t - i
        px[0, y] = tuple(int(couleurs[i][k] + (couleurs[i + 1][k] - couleurs[i][k]) * f) for k in range(3))
    return colonne.resize((w, h))


def texte_or(base, x, y, texte, police, ancre='gauche', ombre=24):
    """Texte rempli d'un dégradé doré avec ombre portée. Retourne (gauche, haut, droite, bas)."""
    d = ImageDraw.Draw(base)
    x0, y0, x1, y1 = d.textbbox((0, 0), texte, font=police)
    tw, th = x1 - x0, y1 - y0
    px = int(x - x0 - (tw / 2 if ancre == 'centre' else tw if ancre == 'droite' else 0))
    py = int(y - y0)
    masque_ombre = Image.new('L', base.size, 0)
    ImageDraw.Draw(masque_ombre).text((px + ombre * 0.4, py + ombre * 0.6), texte, font=police, fill=230)
    base.paste(Image.new('RGB', base.size, (0, 0, 0)), (0, 0), masque_ombre.filter(ImageFilter.GaussianBlur(ombre)))
    masque = Image.new('L', base.size, 0)
    ImageDraw.Draw(masque).text((px, py), texte, font=police, fill=255)
    calque = Image.new('RGB', base.size, OR)
    calque.paste(degrade_vertical(tw + 60, th + 60, [OR_CLAIR, OR, OR_FONCE]), (px + x0 - 30, py + y0 - 30))
    base.paste(calque, (0, 0), masque)
    return px + x0, py + y0, px + x1, py + y1


def texte(d, x, y, contenu, police, couleur, lettrage=0, ancre='gauche'):
    largeurs = [d.textlength(c, font=police) for c in contenu]
    total = sum(largeurs) + lettrage * (len(contenu) - 1)
    if ancre == 'centre':
        x -= total / 2
    elif ancre == 'droite':
        x -= total
    for c, lw in zip(contenu, largeurs):
        d.text((x, y), c, font=police, fill=couleur)
        x += lw + lettrage
    return total


def ligne_invite(d, x, y, taille, ancre='gauche'):
    """« AVEC DJ DANY » : « avec » discret, nom de l'invité en or. Retourne le bas de la ligne."""
    f_avec, f_nom = bahn(taille * 0.55, 'SemiBold'), bahn(taille, 'Bold')
    lettrage = taille * 0.12
    l_avec = sum(d.textlength(c, font=f_avec) for c in 'AVEC') + lettrage * 3
    l_nom = d.textlength(INVITE, font=f_nom)
    ecart = taille * 0.45
    total = l_avec + ecart + l_nom
    x0 = x - total / 2 if ancre == 'centre' else x
    texte(d, x0, y + taille * 0.36, 'AVEC', f_avec, GRIS, lettrage=lettrage)
    d.text((x0 + l_avec + ecart, y), INVITE, font=f_nom, fill=OR_CLAIR)
    return y + taille * 1.15


def icone_tel(d, x, y, t, couleur):
    d.rounded_rectangle([x, y, x + t * 0.62, y + t], radius=t * 0.14, outline=couleur, width=max(3, int(t * 0.09)))
    d.line([x + t * 0.22, y + t * 0.83, x + t * 0.40, y + t * 0.83], fill=couleur, width=max(3, int(t * 0.08)))


def assombrir(base, alpha):
    """Superpose du noir selon un masque d'opacité (tableau numpy 0..1)."""
    masque = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype('uint8'), 'L')
    base.paste(Image.new('RGB', base.size, NOIR), (0, 0), masque)


def photo_plein_cadre(source, W, H):
    """Photo agrandie pour couvrir toute l'affiche, l'artiste décalé vers la gauche."""
    echelle = 1.12 * max(W / source.width, H / source.height)
    pw, ph = int(source.width * echelle), int(source.height * echelle)
    photo = source.resize((pw, ph), Image.LANCZOS)
    visage_x = 0.44 * pw  # position du visage dans la photo d'origine
    gauche = int(np.clip(visage_x - 0.36 * W, 0, pw - W))
    photo = photo.crop((gauche, 0, gauche + W, H))
    photo = ImageEnhance.Contrast(photo).enhance(1.12)
    photo = ImageEnhance.Color(photo).enhance(1.05)
    return photo.filter(ImageFilter.UnsharpMask(radius=4, percent=70, threshold=2))


def generer(nom, largeur_mm, hauteur_mm, source):
    W, H = round(largeur_mm / 25.4 * DPI), round(hauteur_mm / 25.4 * DPI)
    u = H / 100
    affiche = photo_plein_cadre(source, W, H)

    # --- Ambiance : voiles sombres (lisibilité) + halo doré de scène
    xs = np.linspace(0, 1, W)[None, :]
    ys = np.linspace(0, 1, H)[:, None]
    voile = np.zeros((H, W))
    voile = np.maximum(voile, np.clip((xs - 0.50) / 0.16, 0, 1) ** 1.2 * 0.82)        # colonne droite
    voile = np.maximum(voile, np.clip((ys - 0.50) / 0.30, 0, 1) ** 1.1 * 0.94)        # bas (nom, infos)
    voile = np.maximum(voile, np.clip((0.14 - ys) / 0.14, 0, 1) * 0.75)               # haut (bandeau)
    vignette = np.clip(((xs - 0.4) ** 2 + (ys - 0.4) ** 2) ** 0.5 - 0.45, 0, 1) * 0.9
    assombrir(affiche, np.maximum(voile, vignette))

    halo = np.exp(-(((xs - 0.80) / 0.28) ** 2 + ((ys - 0.05) / 0.35) ** 2))
    lumiere = np.array(affiche).astype(float)
    lumiere += halo[..., None] * np.array([70, 52, 10])
    grain = np.random.default_rng(26).normal(0, 5, (H, W, 1))
    affiche = Image.fromarray(np.clip(lumiere + grain, 0, 255).astype('uint8'), 'RGB')

    d = ImageDraw.Draw(affiche)
    marge = int(4.5 * u)

    # --- Bandeau : CJICS présente
    f_org = serif(6.6 * u)
    d.text((marge, 3.2 * u), ORGANISATEUR, font=f_org, fill=OR_CLAIR)
    lo = d.textlength(ORGANISATEUR, font=f_org)
    texte(d, marge + lo + 2 * u, 5.8 * u, 'PRÉSENTE', bahn(2.4 * u, 'SemiBold'), CREME, lettrage=0.5 * u)
    texte(d, W - marge, 5.6 * u, SITE, bahn(2.4 * u, 'SemiBold'), GRIS, ancre='droite')

    # --- Colonne droite : rendez-vous
    xc = W - marge
    texte(d, xc, 15 * u, 'EN CONCERT LIVE', bahn(2.7 * u, 'Bold'), OR, lettrage=0.8 * u, ancre='droite')
    largeur_mois = d.textlength('DÉCEMBRE', font=bahn(5 * u, 'Bold'))
    _, _, _, bas_jour = texte_or(affiche, xc - largeur_mois - 2.4 * u, 18.5 * u, '26', serif(19 * u), ancre='droite', ombre=18)
    d = ImageDraw.Draw(affiche)
    texte(d, xc, 21.5 * u, 'DÉCEMBRE', bahn(5 * u, 'Bold'), CREME, ancre='droite')
    texte(d, xc, 28.2 * u, '2026', bahn(5 * u, 'Light'), CREME, ancre='droite')
    texte(d, xc, bas_jour + 2.6 * u, 'SAMEDI  ·  À PARTIR DE 19H', bahn(3.3 * u, 'Bold'), OR_CLAIR, lettrage=0.15 * u, ancre='droite')
    d.line([(xc - 34 * u, bas_jour + 8.6 * u), (xc, bas_jour + 8.6 * u)], fill=OR_FONCE, width=max(3, int(0.22 * u)))
    texte(d, xc, bas_jour + 10.4 * u, 'Terrain de tennis de la', bahn(2.7 * u, 'Regular'), CREME, ancre='droite')
    texte(d, xc, bas_jour + 13.8 * u, 'Cité Mbaye Mbaye', bahn(2.7 * u, 'Regular'), CREME, ancre='droite')
    texte(d, xc, bas_jour + 17.6 * u, 'MBORO', bahn(3.4 * u, 'Bold'), OR, lettrage=0.9 * u, ancre='droite')

    # --- QR code (coin bas droit)
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=2, box_size=24)
    q.add_data(URL)
    q.make(fit=True)
    cote = int(19 * u)
    qr = q.make_image(fill_color='black', back_color='white').convert('RGB').resize((cote, cote), Image.NEAREST)
    qx, qy = W - marge - cote, int(64 * u)
    d.rounded_rectangle([qx - 1.1 * u, qy - 1.1 * u, qx + cote + 1.1 * u, qy + cote + 1.1 * u], radius=int(1.2 * u), fill='white', outline=OR, width=max(4, int(0.35 * u)))
    affiche.paste(qr, (qx, qy))
    d = ImageDraw.Draw(affiche)
    texte(d, qx + cote / 2, qy + cote + 2.2 * u, 'SCANNEZ & RÉSERVEZ', bahn(2.2 * u, 'Bold'), OR_CLAIR, lettrage=0.2 * u, ancre='centre')

    # --- Nom de l'artiste, en grand, en bas à gauche
    largeur_nom = qx - 4 * u - marge
    titre = taille_ajustee('DIP DOUNDOU GUISS', serif, 16 * u, largeur_nom)
    _, haut_nom, _, bas_nom = texte_or(affiche, marge, 50.5 * u, 'DIP DOUNDOU GUISS', titre, ombre=30)
    d = ImageDraw.Draw(affiche)
    bas_invite = ligne_invite(d, marge + 0.4 * u, bas_nom + 2.2 * u, 4.4 * u)

    # --- Tarifs, sous le nom
    yt = bas_invite + 2.6 * u
    x = marge
    f_etiq, f_prix = bahn(2.2 * u, 'Bold'), bahn(4.2 * u, 'Bold')
    for i, (etiquette, couleur, prix, couleur_prix) in enumerate(TARIFS):
        if i == 2:  # deuxième ligne : VIP
            x, yt = marge, yt + 5.6 * u
        le = texte(d, x, yt + 1.4 * u, etiquette, f_etiq, couleur, lettrage=0.3 * u)
        d.text((x + le + 1.4 * u, yt), prix, font=f_prix, fill=couleur_prix)
        x += le + 1.4 * u + d.textlength(prix, font=f_prix) + 5 * u

    # --- Infoline
    yb = 92.2 * u
    d.line([(marge, 89.8 * u), (qx - 4 * u, 89.8 * u)], fill=OR_FONCE, width=max(3, int(0.2 * u)))
    f_label, f_num = bahn(2.3 * u, 'Bold'), bahn(2.9 * u, 'Bold')
    lw = d.textlength('INFOLINE', font=f_label)
    d.rounded_rectangle([marge, yb - 0.5 * u, marge + lw + 2.4 * u, yb + 3.5 * u], radius=int(0.6 * u), fill=OR)
    d.text((marge + 1.2 * u, yb + 0.3 * u), 'INFOLINE', font=f_label, fill=NOIR)
    x = marge + lw + 5 * u
    for numero in INFOLINE:
        icone_tel(d, x, yb + 0.1 * u, 2.9 * u, OR)
        d.text((x + 3 * u, yb - 0.25 * u), numero, font=f_num, fill=CREME)
        x += 3 * u + d.textlength(numero, font=f_num) + 3.2 * u

    chemin = PROJET / 'public' / nom
    affiche.save(chemin, 'JPEG', quality=92, optimize=True, progressive=True, dpi=(DPI, DPI))
    print(f'{nom} : {W} x {H} px ({largeur_mm / 10:g} x {hauteur_mm / 10:g} cm à {DPI} dpi)')


def generer_flyer(nom, largeur_mm, hauteur_mm, source):
    """Flyer portrait : photo en haut, informations dans la moitié basse."""
    W, H = round(largeur_mm / 25.4 * DPI), round(hauteur_mm / 25.4 * DPI)
    u = H / 100

    # Photo couvrant toute la hauteur, recadrée sur l'artiste
    echelle = max(W / source.width, H / source.height)
    pw, ph = int(source.width * echelle), int(source.height * echelle)
    photo = source.resize((pw, ph), Image.LANCZOS)
    gauche = int(np.clip(0.47 * pw - W / 2, 0, pw - W))
    affiche = photo.crop((gauche, 0, gauche + W, H))
    affiche = ImageEnhance.Contrast(affiche).enhance(1.12)
    affiche = affiche.filter(ImageFilter.UnsharpMask(radius=3, percent=70, threshold=2))

    xs = np.linspace(0, 1, W)[None, :]
    ys = np.linspace(0, 1, H)[:, None]
    voile = np.maximum(np.clip((ys - 0.40) / 0.16, 0, 1) ** 1.1 * 0.93, np.clip((0.12 - ys) / 0.12, 0, 1) * 0.75)
    voile = np.maximum(voile, np.clip(np.abs(xs - 0.5) - 0.36, 0, 1) * 2.2)
    assombrir(affiche, voile)
    halo = np.exp(-(((xs - 0.75) / 0.35) ** 2 + ((ys - 0.04) / 0.25) ** 2))
    lumiere = np.array(affiche).astype(float) + halo[..., None] * np.array([60, 45, 8])
    grain = np.random.default_rng(5).normal(0, 4, (H, W, 1))
    affiche = Image.fromarray(np.clip(lumiere + grain, 0, 255).astype('uint8'), 'RGB')

    d = ImageDraw.Draw(affiche)
    marge = int(5.5 * u * W / H * 1.4)
    cx = W / 2

    # Bandeau
    f_org = serif(5.2 * u)
    d.text((marge, 2.6 * u), ORGANISATEUR, font=f_org, fill=OR_CLAIR)
    texte(d, marge + d.textlength(ORGANISATEUR, font=f_org) + 1.4 * u, 4.6 * u, 'PRÉSENTE', bahn(1.8 * u, 'SemiBold'), CREME, lettrage=0.35 * u)

    # Nom, date, lieu
    largeur_utile = W - 2 * marge
    texte(d, cx, 40.5 * u, 'EN CONCERT LIVE', bahn(2.2 * u, 'Bold'), OR, lettrage=0.6 * u, ancre='centre')
    _, _, _, y = texte_or(affiche, cx, 44 * u, 'DIP DOUNDOU', taille_ajustee('DIP DOUNDOU', serif, 8 * u, largeur_utile), ancre='centre', ombre=16)
    _, _, _, y = texte_or(affiche, cx, y + 1 * u, 'GUISS', serif(9.5 * u), ancre='centre', ombre=16)
    d = ImageDraw.Draw(affiche)
    y = ligne_invite(d, cx, y + 1.6 * u, 3.3 * u, ancre='centre') - 0.4 * u
    date = 'SAMEDI 26 DÉCEMBRE 2026  ·  19H'
    texte(d, cx, y + 2.6 * u, date, taille_ajustee(date, lambda t: bahn(t, 'Bold'), 3 * u, largeur_utile), CREME, ancre='centre')
    lieu = 'Terrain de tennis de la Cité Mbaye Mbaye  ·  MBORO'
    texte(d, cx, y + 6.8 * u, lieu, taille_ajustee(lieu, lambda t: bahn(t, 'SemiBold'), 2 * u, largeur_utile), OR_CLAIR, ancre='centre')

    # Tarifs (gauche) + QR (droite)
    haut_bloc = y + 10 * u
    cote = int(12.4 * u)
    qx, qy = W - marge - cote, int(haut_bloc)
    d.rounded_rectangle([qx - 0.8 * u, qy - 0.8 * u, qx + cote + 0.8 * u, qy + cote + 0.8 * u], radius=int(0.9 * u), fill='white', outline=OR, width=max(3, int(0.25 * u)))
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=2, box_size=24)
    q.add_data(URL)
    q.make(fit=True)
    affiche.paste(q.make_image(fill_color='black', back_color='white').convert('RGB').resize((cote, cote), Image.NEAREST), (qx, qy))
    d = ImageDraw.Draw(affiche)
    texte(d, qx + cote / 2, qy + cote + 1.5 * u, 'SCANNEZ & RÉSERVEZ', bahn(1.45 * u, 'Bold'), OR_CLAIR, ancre='centre')

    yt = grille_tarifs(d, marge, haut_bloc + 0.2 * u, qx - 2.5 * u - marge, u, 1.8 * u, 3.6 * u, 5.9 * u)
    texte(d, marge, yt + 0.1 * u, SITE, bahn(1.9 * u, 'SemiBold'), GRIS)

    # Infoline
    yl = 90.3 * u
    d.line([(marge, yl), (W - marge, yl)], fill=OR_FONCE, width=max(3, int(0.18 * u)))
    numeros = '   ·   '.join(INFOLINE)
    f_label = bahn(1.7 * u, 'Bold')
    lw = d.textlength('INFOLINE', font=f_label)
    d.rounded_rectangle([cx - lw / 2 - 1 * u, yl + 1.2 * u, cx + lw / 2 + 1 * u, yl + 3.8 * u], radius=int(0.5 * u), fill=OR)
    texte(d, cx, yl + 1.55 * u, 'INFOLINE', f_label, NOIR, ancre='centre')
    texte(d, cx, yl + 4.4 * u, numeros, taille_ajustee(numeros, lambda t: bahn(t, 'Bold'), 2.3 * u, largeur_utile), CREME, ancre='centre')

    chemin = PROJET / 'public' / nom
    affiche.save(chemin, 'JPEG', quality=93, optimize=True, progressive=True, dpi=(DPI, DPI))
    print(f'{nom} : {W} x {H} px ({largeur_mm / 10:g} x {hauteur_mm / 10:g} cm à {DPI} dpi)')


def main():
    source = Image.open(PROJET / 'public' / 'artiste.jpeg').convert('RGB')
    for nom, (l, h) in FORMATS.items():
        generer(nom, l, h, source)
    generer_flyer('flyer-a5.jpg', 148, 210, source)


if __name__ == '__main__':
    main()
