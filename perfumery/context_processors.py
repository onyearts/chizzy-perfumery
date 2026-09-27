from django.conf import settings


def payment_context(_request):
    return {'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY}
