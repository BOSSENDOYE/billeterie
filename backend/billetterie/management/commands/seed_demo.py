from django.core.management.base import BaseCommand

from billetterie.services import generer_demo


class Command(BaseCommand):
    help = "Crée l'événement et ses 300 billets. ATTENTION : efface toutes les ventes existantes."

    def add_arguments(self, parser):
        parser.add_argument('--demo', action='store_true', help='Ajoute de fausses ventes (tests uniquement)')

    def handle(self, *args, demo=False, **options):
        ev = generer_demo(vendus=41, scannes=12) if demo else generer_demo()
        self.stdout.write(self.style.SUCCESS(f'Événement « {ev.titre} » créé avec {ev.capacite} billets.'))
