from django.core.management.base import BaseCommand

from perfumery.locations import NIGERIAN_LOCATIONS
from perfumery.models import LocalGovernment, State


class Command(BaseCommand):
    help = 'Create missing Nigerian States and Local Governments from the built-in directory.'

    def handle(self, *args, **options):
        created_states = 0
        created_lgas = 0

        for code, (name, lga_names) in NIGERIAN_LOCATIONS.items():
            state, created = State.objects.get_or_create(
                code=code,
                defaults={'name': name, 'is_active': False},
            )
            created_states += int(created)
            if code == 'FC':
                legacy_amac = LocalGovernment.objects.filter(state=state, name='AMAC').first()
                canonical_amac = LocalGovernment.objects.filter(
                    state=state,
                    name='Abuja Municipal Area Council (AMAC)',
                ).first()
                if legacy_amac and canonical_amac:
                    if canonical_amac.delivery_fee is None and legacy_amac.delivery_fee is not None:
                        canonical_amac.delivery_fee = legacy_amac.delivery_fee
                        canonical_amac.estimated_days = legacy_amac.estimated_days
                        canonical_amac.save(update_fields=['delivery_fee', 'estimated_days'])
                    legacy_amac.delete()
                elif legacy_amac:
                    legacy_amac.name = 'Abuja Municipal Area Council (AMAC)'
                    legacy_amac.save(update_fields=['name'])
            for lga_name in lga_names:
                _lga, created = LocalGovernment.objects.get_or_create(
                    state=state,
                    name=lga_name,
                    defaults={
                        'delivery_fee': None,
                        'estimated_days': '1–3 business days',
                        'is_active': True,
                    },
                )
                created_lgas += int(created)

        self.stdout.write(self.style.SUCCESS(
            f'Location directory ready: {created_states} states and {created_lgas} local governments added.'
        ))
