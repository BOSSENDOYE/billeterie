from django.core.management.base import BaseCommand

from billetterie.models import Evenement
from billetterie.services import generer_demo


class Command(BaseCommand):
    help = "Crée l'événement et ses 300 billets. ATTENTION : efface toutes les ventes existantes."

    def add_arguments(self, parser):
        parser.add_argument('--demo', action='store_true', help='Ajoute de fausses ventes (tests uniquement)')
        parser.add_argument('--si-vide', action='store_true', help="Ne fait rien si un événement existe déjà (démarrage Docker)")

    def handle(self, *args, demo=False, si_vide=False, **options):
        if si_vide and Evenement.objects.exists():
            self.stdout.write('Événement déjà présent : aucune modification.')
            return
        ev = generer_demo(vendus=41, scannes=12) if demo else generer_demo()
        self.stdout.write(self.style.SUCCESS(f'Événement « {ev.titre} » créé avec {ev.capacite} billets.'))
