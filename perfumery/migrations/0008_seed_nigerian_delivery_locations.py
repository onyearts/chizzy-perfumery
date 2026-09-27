from django.db import migrations

from perfumery.locations import NIGERIAN_LOCATIONS


STATE_ALIASES = {
    name.casefold(): code
    for code, (name, _lgas) in NIGERIAN_LOCATIONS.items()
}
STATE_ALIASES.update({
    f'{name} state'.casefold(): code
    for code, (name, _lgas) in NIGERIAN_LOCATIONS.items()
    if code != 'FC'
})
STATE_ALIASES.update({
    'fct': 'FC',
    'abuja': 'FC',
    'federal capital territory': 'FC',
})


def seed_all_nigerian_locations(apps, schema_editor):
    State = apps.get_model('perfumery', 'State')
    LocalGovernment = apps.get_model('perfumery', 'LocalGovernment')
    database = schema_editor.connection.alias
    legacy_codes = {'NG-LA': 'LA', 'NG-OG': 'OG', 'NG-FC': 'FC'}

    for state in State.objects.using(database).all():
        code = legacy_codes.get(state.code, state.code) or STATE_ALIASES.get(state.name.strip().casefold())
        if code not in NIGERIAN_LOCATIONS:
            continue
        name, lga_names = NIGERIAN_LOCATIONS[code]
        State.objects.using(database).filter(pk=state.pk).update(code=code, name=name)
        LocalGovernment.objects.using(database).filter(state_id=state.pk).exclude(name__in=lga_names).update(is_active=False)
        # A prior default of zero could mean either free or never configured.
        # Treat it as unset so checkout cannot silently promise free delivery.
        LocalGovernment.objects.using(database).filter(state_id=state.pk, delivery_fee=0).update(delivery_fee=None)
        for lga_name in lga_names:
            LocalGovernment.objects.using(database).get_or_create(
                state_id=state.pk,
                name=lga_name,
                defaults={'delivery_fee': None, 'estimated_days': '1–3 business days', 'is_active': True},
            )

    for code, (name, lga_names) in NIGERIAN_LOCATIONS.items():
        state, _ = State.objects.using(database).get_or_create(
            code=code,
            defaults={'name': name, 'is_active': True},
        )
        for lga_name in lga_names:
            LocalGovernment.objects.using(database).get_or_create(
                state_id=state.pk,
                name=lga_name,
                defaults={'delivery_fee': None, 'estimated_days': '1–3 business days', 'is_active': True},
            )


class Migration(migrations.Migration):
    dependencies = [
        ('perfumery', '0007_alter_localgovernment_delivery_fee_alter_state_code'),
    ]

    operations = [
        migrations.RunPython(seed_all_nigerian_locations, migrations.RunPython.noop),
    ]
