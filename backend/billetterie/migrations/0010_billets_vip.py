from django.db import migrations, models

TYPES = [('prevente', 'Prévente'), ('jour_j', 'Jour J'), ('vip', 'VIP'), ('vvip', 'VVIP')]


def creer_billets_vip(apps, schema_editor):
    """Événements existants : 100 billets VIP (10 000 F) et 50 billets VVIP (25 000 F)."""
    Evenement = apps.get_model('billetterie', 'Evenement')
    Ticket = apps.get_model('billetterie', 'Ticket')
    for ev in Evenement.objects.all():
        for type_billet, quota in (('vip', ev.quota_vip), ('vvip', ev.quota_vvip)):
            existants = set(Ticket.objects.filter(evenement=ev, type=type_billet).values_list('numero', flat=True))
            Ticket.objects.bulk_create(
                Ticket(evenement=ev, type=type_billet, numero=n) for n in range(1, quota + 1) if n not in existants
            )
        ev.capacite = ev.quota_prevente + ev.quota_jour_j + ev.quota_vip + ev.quota_vvip
        ev.save(update_fields=['capacite'])


class Migration(migrations.Migration):
    dependencies = [('billetterie', '0009_paiement_wave_checkout')]

    operations = [
        migrations.AddField('evenement', 'prix_vip', models.PositiveIntegerField(default=10000, help_text='Prix VIP, en FCFA')),
        migrations.AddField('evenement', 'prix_vvip', models.PositiveIntegerField(default=25000, help_text='Prix VVIP, en FCFA')),
        migrations.AddField('evenement', 'quota_vip', models.PositiveIntegerField(
            default=100, help_text='Nombre de billets VIP (augmenter crée les billets manquants)')),
        migrations.AddField('evenement', 'quota_vvip', models.PositiveIntegerField(
            default=50, help_text='Nombre de billets VVIP (augmenter crée les billets manquants)')),
        migrations.AlterField('evenement', 'capacite', models.PositiveIntegerField(default=750, help_text='Total de toutes les séries')),
        migrations.AlterField('ticket', 'type', models.CharField(choices=TYPES, db_index=True, default='prevente', max_length=10)),
        migrations.AlterField('paiement', 'type', models.CharField(choices=TYPES, default='prevente', max_length=10)),
        migrations.RunPython(creer_billets_vip, migrations.RunPython.noop),
    ]
