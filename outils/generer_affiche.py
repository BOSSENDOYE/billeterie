"""Affiche A4 (300 dpi) — Dip Doundou Guiss, Mboro — avec QR code vers la billetterie.

Usage (depuis la racine du projet, sous Windows pour les polices) :
    pip install qrcode pillow
    python outils/generer_affiche.py        ->  public/affiche.jpg
"""
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

PROJET = str(Path(__file__).resolve().parent.parent)
SORTIE = PROJET + '/public/affiche.jpg'
URL = 'https://billet.cml-sst.com'

W, H = 2480, 3508
NOIR = (10, 10, 11)
OR_CLAIR, OR, OR_FONCE = (240, 215, 140), (212, 175, 55), (140, 109, 31)
CREME = (244, 241, 234)
GRIS = (175, 172, 165)

FONTS = 'C:/Windows/Fonts/'


def bahn(taille, style):
    f = ImageFont.truetype(FONTS + 'bahnschrift.ttf', taille)
    f.set_variation_by_name(style)
    return f


def serif(taille):
    return ImageFont.truetype(FONTS + 'georgiab.ttf', taille)


def degrade_vertical(w, h, couleurs):
    """Dégradé vertical multi-couleurs (pour le texte doré)."""
    img = Image.new('RGB', (w, h))
    px = img.load()
    n = len(couleurs) - 1
    for y in range(h):
        t = y / max(h - 1, 1) * n
        i = min(int(t), n - 1)
        f = t - i
        c = tuple(int(couleurs[i][k] + (couleurs[i + 1][k] - couleurs[i][k]) * f) for k in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def texte_or(base, xy_centre, texte, police, espacement=0):
    """Texte centré rempli d'un dégradé doré, avec une ombre douce."""
    d = ImageDraw.Draw(base)
    bbox = d.textbbox((0, 0), texte, font=police, spacing=espacement)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = int(xy_centre[0] - tw / 2 - bbox[0])
    y = int(xy_centre[1] - bbox[1])
    # ombre
    ombre = Image.new('L', base.size, 0)
    ImageDraw.Draw(ombre).text((x + 8, y + 12), texte, font=police, fill=200)
    ombre = ombre.filter(ImageFilter.GaussianBlur(18))
    base.paste(Image.new('RGB', base.size, (0, 0, 0)), (0, 0), ombre)
    # remplissage doré
    masque = Image.new('L', base.size, 0)
    ImageDraw.Draw(masque).text((x, y), texte, font=police, fill=255)
    gradient = degrade_vertical(tw + 20, th + 20, [OR_CLAIR, OR, OR_FONCE]).resize((tw + 20, th + 20))
    calque = Image.new('RGB', base.size, OR)
    calque.paste(gradient, (x + bbox[0] - 10, y + bbox[1] - 10))
    base.paste(calque, (0, 0), masque)
    return y + bbox[3]


def texte_centre(d, y, texte, police, couleur, lettrage=0):
    if lettrage:
        largeurs = [d.textlength(c, font=police) for c in texte]
        total = sum(largeurs) + lettrage * (len(texte) - 1)
        x = (W - total) / 2
        for c, lw in zip(texte, largeurs):
            d.text((x, y), c, font=police, fill=couleur)
            x += lw + lettrage
        return
    tw = d.textlength(texte, font=police)
    d.text(((W - tw) / 2, y), texte, font=police, fill=couleur)


def main():
    affiche = Image.new('RGB', (W, H), NOIR)

    # --- Photo de l'artiste (haut de l'affiche), fondue vers le noir
    photo = Image.open(PROJET + '/public/artiste.jpeg').convert('RGB')
    ph = int(photo.height * W / photo.width)
    photo = photo.resize((W, ph), Image.LANCZOS)
    photo = ImageEnhance.Contrast(photo).enhance(1.08)
    photo = ImageEnhance.Brightness(photo).enhance(0.92)
    photo = photo.filter(ImageFilter.UnsharpMask(radius=3, percent=60, threshold=2))
    affiche.paste(photo, (0, 0))

    voile = Image.new('L', (W, H), 0)
    dv = ImageDraw.Draw(voile)
    debut, fin = int(ph * 0.45), ph
    for y in range(debut, H):
        a = 255 if y >= fin else int(255 * ((y - debut) / (fin - debut)) ** 1.4)
        dv.line([(0, y), (W, y)], fill=a)
    for y in range(0, 420):  # assombrit le haut pour le bandeau
        dv.line([(0, y), (W, y)], fill=int(150 * (1 - y / 420)))
    affiche.paste(Image.new('RGB', (W, H), NOIR), (0, 0), voile)

    d = ImageDraw.Draw(affiche)

    # --- Bandeau du haut
    texte_centre(d, 150, 'EN CONCERT LIVE', bahn(78, 'SemiBold'), OR, lettrage=28)
    d.line([(W / 2 - 520, 280), (W / 2 - 120, 280)], fill=OR, width=4)
    d.line([(W / 2 + 120, 280), (W / 2 + 520, 280)], fill=OR, width=4)
    d.regular_polygon((W / 2, 280, 16), 4, rotation=45, fill=OR)

    # --- Nom de l'artiste
    y = texte_or(affiche, (W / 2, 1480), 'DIP DOUNDOU', serif(300))
    y = texte_or(affiche, (W / 2, y + 30), 'GUISS', serif(360))
    d = ImageDraw.Draw(affiche)

    # --- Date, heure, lieu
    y += 95
    texte_centre(d, y, 'SAMEDI 26 DÉCEMBRE 2026  ·  20H', bahn(112, 'Bold'), CREME, lettrage=4)
    y += 160
    texte_centre(d, y, 'Terrain de tennis de la Cité Mbaye Mbaye  ·  MBORO', bahn(72, 'SemiBold'), OR_CLAIR)

    # --- Bloc billetterie : prix à gauche, QR à droite
    haut = y + 150
    marge = 150
    hauteur = 860
    d.rounded_rectangle([marge, haut, W - marge, haut + hauteur], radius=48, outline=OR, width=5, fill=(18, 18, 20))

    gx = marge + 100
    d.text((gx, haut + 95), 'ENTRÉE', font=bahn(68, 'SemiBold'), fill=GRIS)
    d.text((gx, haut + 165), '2 500', font=serif(250), fill=OR_CLAIR)
    d.text((gx + 8, haut + 445), 'FCFA', font=bahn(110, 'Bold'), fill=OR)
    d.text((gx, haut + 600), 'Paiement Wave', font=bahn(70, 'SemiBold'), fill=CREME)
    d.text((gx, haut + 685), '300 places seulement', font=bahn(60, 'Regular'), fill=GRIS)

    # QR code (correction H : reste lisible même abîmé, froissé ou mal imprimé)
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=2, box_size=24)
    q.add_data(URL)
    q.make(fit=True)
    qr = q.make_image(fill_color='black', back_color='white').convert('RGB')
    cote = 660
    qr = qr.resize((cote, cote), Image.NEAREST)
    qx, qy = W - marge - 90 - cote, haut + 55
    d.rounded_rectangle([qx - 24, qy - 24, qx + cote + 24, qy + cote + 24], radius=28, fill='white')
    affiche.paste(qr, (qx, qy))
    d = ImageDraw.Draw(affiche)
    legende = 'SCANNEZ POUR RÉSERVER'
    f = bahn(56, 'Bold')
    d.text((qx + cote / 2 - d.textlength(legende, font=f) / 2, qy + cote + 45), legende, font=f, fill=OR_CLAIR)

    # --- Pied de page
    texte_centre(d, haut + hauteur + 55, 'billet.cml-sst.com', bahn(84, 'SemiBold'), CREME, lettrage=4)
    texte_centre(d, H - 105, 'Billet nominatif à QR code  ·  Un billet = une entrée', bahn(50, 'Regular'), GRIS)

    affiche.save(SORTIE, 'JPEG', quality=92, optimize=True, progressive=True, dpi=(300, 300))
    print('Affiche :', SORTIE, affiche.size)


if __name__ == '__main__':
    main()
