from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db import migrations

DAKAR = ZoneInfo('Africa/Dakar')


def configurer(apps, schema_editor):
    """Événement existant : 400 billets prévente (2 500 F) + 200 billets Jour J (3 000 F).

    Les billets déjà créés (et vendus) sont conservés : ce sont des billets prévente.
    """
    Evenement = apps.get_model('billetterie', 'Evenement')
    Ticket = apps.get_model('billetterie', 'Ticket')
    for ev in Evenement.objects.all():
        ev.prix_jour_j = 3000
        ev.quota_prevente = 400
        ev.quota_jour_j = 200
        ev.capacite = 600
        # Fin de prévente : la veille à minuit (début du jour du concert, heure de Dakar)
        jour = ev.date.astimezone(DAKAR).date()
        ev.fin_prevente = datetime.combine(jour, time(0, 0), tzinfo=DAKAR)
        ev.save()

        for type_billet, quota in (('prevente', 400), ('jour_j', 200)):
            existants = set(Ticket.objects.filter(evenement=ev, type=type_billet).values_list('numero', flat=True))
            Ticket.objects.bulk_create(
                Ticket(evenement=ev, type=type_billet, numero=n) for n in range(1, quota + 1) if n not in existants
            )


class Migration(migrations.Migration):
    dependencies = [('billetterie', '0004_types_billets')]
    operations = [migrations.RunPython(configurer, migrations.RunPython.noop)]
