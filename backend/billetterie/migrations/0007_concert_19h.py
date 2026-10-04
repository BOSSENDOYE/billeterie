from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import migrations

DAKAR = ZoneInfo('Africa/Dakar')


def passer_a_19h(apps, schema_editor):
    """Concert du 26/12/2026 : début à 19h (bases déjà initialisées à 20h ou 21h)."""
    Evenement = apps.get_model('billetterie', 'Evenement')
    Evenement.objects.filter(
        date__in=[datetime(2026, 12, 26, h, 0, tzinfo=DAKAR) for h in (20, 21)]
    ).update(date=datetime(2026, 12, 26, 19, 0, tzinfo=DAKAR))


class Migration(migrations.Migration):
    dependencies = [('billetterie', '0006_billets_physiques')]
    operations = [migrations.RunPython(passer_a_19h, migrations.RunPython.noop)]
