from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import migrations

DAKAR = ZoneInfo('Africa/Dakar')


def passer_a_20h(apps, schema_editor):
    """Concert du 26/12/2026 : début à 20h au lieu de 21h (bases déjà initialisées)."""
    Evenement = apps.get_model('billetterie', 'Evenement')
    Evenement.objects.filter(date=datetime(2026, 12, 26, 21, 0, tzinfo=DAKAR)).update(
        date=datetime(2026, 12, 26, 20, 0, tzinfo=DAKAR)
    )


class Migration(migrations.Migration):
    dependencies = [('billetterie', '0002_paiement_declare_le_paiement_transaction_wave_and_more')]
    operations = [migrations.RunPython(passer_a_20h, migrations.RunPython.noop)]
