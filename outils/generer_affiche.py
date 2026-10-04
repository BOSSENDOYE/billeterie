"""Affiches paysage (300 dpi) — Dip Doundou Guiss, Mboro — CJICS présente.

Génère :
    public/affiche.jpg         A3 paysage (42 x 29,7 cm)  — servie sur le site (/affiche.jpg)
    public/affiche-40x30.jpg   40 x 30 cm paysage

Usage (depuis la racine du projet, sous Windows pour les polices) :
    pip install qrcode pillow
    python outils/generer_affiche.py
"""
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

PROJET = Path(__file__).resolve().parent.parent
URL = 'https://billeteriecjics.com'
SITE = 'billeteriecjics.com'
ORGANISATEUR = 'CJICS'
INFOLINE = ['+221 71 161 95 47', '+221 77 370 01 07', '+221 78 602 95 98']

DPI = 300
FORMATS = {
    'affiche.jpg': (420, 297),        # A3 paysage, en mm
    'affiche-40x30.jpg': (400, 300),  # 40 x 30 cm paysage
}

NOIR = (10, 10, 11)
OR_CLAIR, OR, OR_FONCE = (240, 215, 140), (212, 175, 55), (140, 109, 31)
CREME = (244, 241, 234)
GRIS = (175, 172, 165)
RUBIS = (224, 49, 75)

FONTS = 'C:/Windows/Fonts/'


def bahn(taille, style):
    f = ImageFont.truetype(FONTS + 'bahnschrift.ttf', int(taille))
    f.set_variation_by_name(style)
    return f


def serif(taille):
    return ImageFont.truetype(FONTS + 'georgiab.ttf', int(taille))


def degrade_vertical(w, h, couleurs):
    """Dégradé vertical (pour le texte doré)."""
    colonne = Image.new('RGB', (1, h))
    px = colonne.load()
    n = len(couleurs) - 1
    for y in range(h):
        t = y / max(h - 1, 1) * n
        i = min(int(t), n - 1)
        f = t - i
        px[0, y] = tuple(int(couleurs[i][k] + (couleurs[i + 1][k] - couleurs[i][k]) * f) for k in range(3))
    return colonne.resize((w, h))


def texte_or(base, cx, y, texte, police):
    """Texte centré sur cx, rempli d'un dégradé doré avec ombre douce. Retourne le bas du texte."""
    d = ImageDraw.Draw(base)
    x0, y0, x1, y1 = d.textbbox((0, 0), texte, font=police)
    tw, th = x1 - x0, y1 - y0
    x, yy = int(cx - tw / 2 - x0), int(y - y0)
    ombre = Image.new('L', base.size, 0)
    ImageDraw.Draw(ombre).text((x + 10, yy + 14), texte, font=police, fill=200)
    base.paste(Image.new('RGB', base.size, (0, 0, 0)), (0, 0), ombre.filter(ImageFilter.GaussianBlur(20)))
    masque = Image.new('L', base.size, 0)
    ImageDraw.Draw(masque).text((x, yy), texte, font=police, fill=255)
    calque = Image.new('RGB', base.size, OR)
    calque.paste(degrade_vertical(tw + 40, th + 40, [OR_CLAIR, OR, OR_FONCE]), (x + x0 - 20, yy + y0 - 20))
    base.paste(calque, (0, 0), masque)
    return yy + y1


def taille_ajustee(texte, fabrique, taille_max, largeur_max):
    """Plus grande taille (<= taille_max) pour laquelle le texte tient dans largeur_max."""
    taille = taille_max
    mesure = ImageDraw.Draw(Image.new('L', (1, 1)))
    while taille > 10 and mesure.textlength(texte, font=fabrique(taille)) > largeur_max:
        taille *= 0.96
    return fabrique(taille)


def texte_centre(d, cx, y, texte, police, couleur, lettrage=0):
    largeurs = [d.textlength(c, font=police) for c in texte]
    total = sum(largeurs) + lettrage * (len(texte) - 1)
    x = cx - total / 2
    for c, lw in zip(texte, largeurs):
        d.text((x, y), c, font=police, fill=couleur)
        x += lw + lettrage
    return total


def icone_tel(d, x, y, t, couleur):
    """Petit combiné téléphonique dessiné (les polices système n'ont pas toutes l'emoji)."""
    d.rounded_rectangle([x, y, x + t * 0.62, y + t], radius=t * 0.14, outline=couleur, width=max(3, int(t * 0.09)))
    d.line([x + t * 0.22, y + t * 0.83, x + t * 0.40, y + t * 0.83], fill=couleur, width=max(3, int(t * 0.08)))


def generer(nom, largeur_mm, hauteur_mm, photo_source):
    W, H = round(largeur_mm / 25.4 * DPI), round(hauteur_mm / 25.4 * DPI)
    u = H / 100  # unité : 1 % de la hauteur
    affiche = Image.new('RGB', (W, H), NOIR)

    # --- Photo de l'artiste à gauche, fondue vers le noir à droite
    ph = H
    pw = int(photo_source.width * ph / photo_source.height)
    photo = photo_source.resize((pw, ph), Image.LANCZOS)
    zone = int(W * 0.56)
    centre_visage = int(pw * 0.44)
    gauche = max(0, min(pw - zone, centre_visage - zone // 2))
    photo = photo.crop((gauche, 0, gauche + zone, ph))
    photo = ImageEnhance.Contrast(photo).enhance(1.08)
    photo = photo.filter(ImageFilter.UnsharpMask(radius=3, percent=60, threshold=2))
    affiche.paste(photo, (0, 0))

    voile = Image.new('L', (W, H), 0)
    dv = ImageDraw.Draw(voile)
    debut, fin = int(W * 0.30), zone
    for x in range(debut, W):
        a = 255 if x >= fin else int(255 * ((x - debut) / (fin - debut)) ** 1.3)
        dv.line([(x, 0), (x, H)], fill=a)
    affiche.paste(Image.new('RGB', (W, H), NOIR), (0, 0), voile)
    # Assombrit le haut (bandeau) et le bas (infoline) sur toute la largeur
    voile2 = Image.new('L', (W, H), 0)
    dv2 = ImageDraw.Draw(voile2)
    for y in range(int(12 * u)):
        dv2.line([(0, y), (W, y)], fill=int(190 * (1 - y / (12 * u))))
    for y in range(int(78 * u), H):
        dv2.line([(0, y), (W, y)], fill=int(235 * min(1, (y - 78 * u) / (10 * u))))
    affiche.paste(Image.new('RGB', (W, H), NOIR), (0, 0), voile2)

    d = ImageDraw.Draw(affiche)
    marge = int(4 * u)

    # --- Bandeau du haut : CJICS présente
    f_org = serif(7.2 * u)
    d.text((marge, 2.6 * u), ORGANISATEUR, font=f_org, fill=OR_CLAIR)
    largeur_org = d.textlength(ORGANISATEUR, font=f_org)
    d.text((marge + largeur_org + 2.2 * u, 5.4 * u), 'PRÉSENTE', font=bahn(2.6 * u, 'SemiBold'), fill=CREME)
    d.line([(marge, 12 * u), (W - marge, 12 * u)], fill=OR_FONCE, width=max(3, int(0.25 * u)))
    f_site = bahn(2.4 * u, 'SemiBold')
    d.text((W - marge - d.textlength(SITE, font=f_site), 5.6 * u), SITE, font=f_site, fill=GRIS)

    # --- Colonne droite : concert
    gauche_col, droite_col = int(W * 0.50), W - marge
    cx = (gauche_col + droite_col) / 2
    largeur_col = droite_col - gauche_col
    texte_centre(d, cx, 16 * u, 'EN CONCERT LIVE', bahn(2.8 * u, 'SemiBold'), OR, lettrage=0.9 * u)
    y = texte_or(affiche, cx, 21.5 * u, 'DIP DOUNDOU', taille_ajustee('DIP DOUNDOU', serif, 9.6 * u, largeur_col * 0.98))
    y = texte_or(affiche, cx, y + 1.2 * u, 'GUISS', serif(11.5 * u))
    d = ImageDraw.Draw(affiche)
    date = 'SAMEDI 26 DÉCEMBRE 2026  ·  19H'
    texte_centre(d, cx, y + 3.2 * u, date, taille_ajustee(date, lambda t: bahn(t, 'Bold'), 4.1 * u, largeur_col * 0.95), CREME, lettrage=0.15 * u)
    lieu = 'Terrain de tennis de la Cité Mbaye Mbaye  ·  MBORO'
    texte_centre(d, cx, y + 9.3 * u, lieu, taille_ajustee(lieu, lambda t: bahn(t, 'SemiBold'), 2.6 * u, largeur_col * 0.95), OR_CLAIR)

    # --- Bloc billetterie : tarifs + QR
    bx0, by0, bx1 = gauche_col, int(y + 14 * u), droite_col
    bh = 85 * u - by0  # le bloc descend jusqu'au-dessus de l'Infoline
    d.rounded_rectangle([bx0, by0, bx1, by0 + bh], radius=int(1.6 * u), outline=OR, width=max(4, int(0.3 * u)), fill=(18, 18, 20))

    qr_cote = int(min(bh - 8 * u, (bx1 - bx0) * 0.36))
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=2, box_size=24)
    q.add_data(URL)
    q.make(fit=True)
    qr = q.make_image(fill_color='black', back_color='white').convert('RGB').resize((qr_cote, qr_cote), Image.NEAREST)
    qx, qy = bx1 - int(2.4 * u) - qr_cote, by0 + int(2 * u)
    d.rounded_rectangle([qx - 0.8 * u, qy - 0.8 * u, qx + qr_cote + 0.8 * u, qy + qr_cote + 0.8 * u], radius=int(0.9 * u), fill='white')
    affiche.paste(qr, (qx, qy))
    d = ImageDraw.Draw(affiche)
    leg = 'SCANNEZ POUR RÉSERVER'
    f_leg = bahn(1.9 * u, 'Bold')
    d.text((qx + qr_cote / 2 - d.textlength(leg, font=f_leg) / 2, qy + qr_cote + 1.5 * u), leg, font=f_leg, fill=OR_CLAIR)

    gx = bx0 + int(2.4 * u)
    by0 = by0 + max(0, (bh - 22 * u) / 2)  # contenu des tarifs centré dans le bloc
    d.text((gx, by0 + 2.2 * u), 'PRÉVENTE', font=bahn(2.4 * u, 'Bold'), fill=OR)
    f_prix = serif(7.6 * u)
    d.text((gx, by0 + 4.6 * u), '2 500', font=f_prix, fill=OR_CLAIR)
    d.text((gx + d.textlength('2 500', font=f_prix) + 1.2 * u, by0 + 9 * u), 'FCFA', font=bahn(3 * u, 'Bold'), fill=OR)
    sep = by0 + 14.2 * u
    d.line([(gx, sep), (qx - 3 * u, sep)], fill=(60, 55, 45), width=max(3, int(0.15 * u)))
    d.text((gx, sep + 1.2 * u), 'JOUR J', font=bahn(2.4 * u, 'Bold'), fill=RUBIS)
    d.text((gx + 9.5 * u, sep + 0.5 * u), '3 000 FCFA', font=bahn(3.6 * u, 'Bold'), fill=CREME)
    d.text((gx, sep + 5.2 * u), '600 places seulement', font=bahn(2.1 * u, 'Regular'), fill=GRIS)

    # --- Pied de page : Infoline
    d.line([(marge, 89 * u), (W - marge, 89 * u)], fill=OR_FONCE, width=max(3, int(0.25 * u)))
    f_info = bahn(3.1 * u, 'Bold')
    f_label = bahn(2.5 * u, 'Bold')
    yb = 91.6 * u
    elements = [('label', 'INFOLINE')] + [('num', n) for n in INFOLINE]
    ecart = 3.2 * u
    largeurs = []
    for type_, t in elements:
        lw = d.textlength(t, font=f_label if type_ == 'label' else f_info)
        largeurs.append(lw + (3.2 * u if type_ == 'num' else 0))
    total = sum(largeurs) + ecart * (len(elements) - 1)
    x = (W - total) / 2
    for (type_, t), lw in zip(elements, largeurs):
        if type_ == 'label':
            d.rounded_rectangle([x - 1.2 * u, yb - 0.4 * u, x + lw + 1.2 * u, yb + 3.6 * u], radius=int(0.6 * u), fill=OR)
            d.text((x, yb + 0.35 * u), t, font=f_label, fill=NOIR)
            x += lw + ecart + 1.2 * u
        else:
            icone_tel(d, x, yb + 0.1 * u, 3.0 * u, OR)
            d.text((x + 3.2 * u, yb - 0.2 * u), t, font=f_info, fill=CREME)
            x += lw + ecart

    chemin = PROJET / 'public' / nom
    affiche.save(chemin, 'JPEG', quality=92, optimize=True, progressive=True, dpi=(DPI, DPI))
    print(f'{nom} : {W} x {H} px ({largeur_mm / 10:g} x {hauteur_mm / 10:g} cm à {DPI} dpi)')


def main():
    photo = Image.open(PROJET / 'public' / 'artiste.jpeg').convert('RGB')
    for nom, (l, h) in FORMATS.items():
        generer(nom, l, h, photo)


if __name__ == '__main__':
    main()
