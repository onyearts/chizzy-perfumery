from django.db import migrations


def merge_legacy_amac_name(apps, schema_editor):
    State = apps.get_model('perfumery', 'State')
    LocalGovernment = apps.get_model('perfumery', 'LocalGovernment')
    database = schema_editor.connection.alias
    for state in State.objects.using(database).filter(code='FC'):
        old = LocalGovernment.objects.using(database).filter(state_id=state.pk, name='AMAC').first()
        if not old:
            continue
        canonical = LocalGovernment.objects.using(database).filter(
            state_id=state.pk,
            name='Abuja Municipal Area Council (AMAC)',
        ).first()
        if canonical:
            if canonical.delivery_fee is None and old.delivery_fee is not None:
                canonical.delivery_fee = old.delivery_fee
                canonical.estimated_days = old.estimated_days
                canonical.save(using=database, update_fields=['delivery_fee', 'estimated_days'])
            old.delete(using=database)
        else:
            old.name = 'Abuja Municipal Area Council (AMAC)'
            old.save(using=database, update_fields=['name'])


class Migration(migrations.Migration):
    dependencies = [
        ('perfumery', '0008_seed_nigerian_delivery_locations'),
    ]

    operations = [
        migrations.RunPython(merge_legacy_amac_name, migrations.RunPython.noop),
    ]
