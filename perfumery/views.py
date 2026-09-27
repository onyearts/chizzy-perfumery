from difflib import SequenceMatcher
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from allauth.socialaccount.models import SocialAccount

from .forms import CheckoutForm, CustomerAddressForm, ProfilePictureForm
from .locations import NIGERIAN_LOCATIONS
from .models import CustomerProfile, LocalGovernment, Product, State


def ranked_products(query, limit=None):
    normalized_query = ' '.join(query.casefold().split())
    query_tokens = normalized_query.split()
    ranked = []

    for product in Product.objects.filter(is_active=True).select_related('category'):
        fields = [product.name, product.brand, product.description]
        if product.category:
            fields.append(product.category.name)
        fields = [' '.join(value.casefold().split()) for value in fields if value]
        combined = ' '.join(fields)
        substring_match = normalized_query in combined

        if substring_match:
            score = 1.0
        elif query_tokens:
            token_scores = [
                max((SequenceMatcher(None, token, word).ratio() for word in combined.split()), default=0)
                for token in query_tokens
            ]
            coverage = sum(score >= 0.72 for score in token_scores) / len(query_tokens)
            phrase_score = max((SequenceMatcher(None, normalized_query, field).ratio() for field in fields), default=0)
            score = max(coverage * 0.9, phrase_score)
        else:
            score = 0.0

        ranked.append((score, product))

    ranked.sort(key=lambda result: (-result[0], result[1].name.casefold()))
    if limit is not None:
        ranked = ranked[:limit]
    return ranked


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('category')
    return render(request, 'perfumery/product_list.html', {'products': products})


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category'),
        slug=slug,
        is_active=True,
    )
    return render(request, 'perfumery/product_detail.html', {'product': product})


def search_products(request):
    query = request.GET.get('q', '').strip()
    ranked = ranked_products(query) if query else []
    normalized_query = ' '.join(query.casefold().split())

    def is_literal_match(product):
        fields = [product.name, product.brand, product.description]
        if product.category:
            fields.append(product.category.name)
        return any(normalized_query in ' '.join(value.casefold().split()) for value in fields if value)

    matches = [product for _, product in ranked if is_literal_match(product)]
    matched_ids = {product.id for product in matches}
    suggestions = [product for _, product in ranked if product.id not in matched_ids][:6]
    return render(
        request,
        'perfumery/search_results.html',
        {'query': query, 'products': matches, 'suggestions': suggestions},
    )


def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'suggestions': []})

    suggestions = [
        {
            'name': product.name,
            'brand': product.brand,
            'price': str(product.price),
            'url': product.get_absolute_url(),
        }
        for _, product in ranked_products(query, limit=5)
    ]
    return JsonResponse({'suggestions': suggestions})


def cart_context(request):
    cart = request.session.get('cart', {})
    quantity = sum(
        item_quantity
        for item_quantity in cart.values()
        if isinstance(item_quantity, int) and item_quantity > 0
    ) if isinstance(cart, dict) else 0
    return {'cart_quantity': quantity}


@login_required
def account_dashboard(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    return render(request, 'perfumery/account.html', {
        'profile': profile,
        'full_name': request.user.get_full_name().strip() or request.user.get_username(),
    })


@login_required
def account_delivery_address(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = CustomerAddressForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your default delivery address has been updated.')
            return redirect('perfumery:account_delivery_address')
    else:
        form = CustomerAddressForm(instance=profile)

    return render(request, 'perfumery/account_delivery_address.html', {'form': form})


@login_required
def account_settings(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        picture_form = ProfilePictureForm(request.POST, request.FILES, instance=profile)
        if picture_form.is_valid():
            picture_form.save()
            messages.success(request, 'Your profile picture has been updated.')
            return redirect('perfumery:account_settings')
    else:
        picture_form = ProfilePictureForm(instance=profile)

    connected_providers = set(
        SocialAccount.objects.filter(user=request.user).values_list('provider', flat=True)
    )
    return render(request, 'perfumery/account_settings.html', {
        'profile': profile,
        'picture_form': picture_form,
        'connected_providers': connected_providers,
    })


def social_auth_context(_request):
    from django.conf import settings

    providers = settings.SOCIALACCOUNT_PROVIDERS
    return {
        'social_auth': {
            provider: any(
                app.get('client_id') and app.get('secret')
                for app in providers.get(provider, {}).get('APPS', [])
            )
            for provider in ('google', 'facebook')
        }
    }


def cart_detail(request):
    items, total = get_cart_items_and_total(request)
    return render(request, 'perfumery/cart.html', {'items': items, 'total': total})


def get_cart_items_and_total(request):
    cart = request.session.get('cart', {})
    if not isinstance(cart, dict):
        cart = {}

    product_ids = [int(product_id) for product_id in cart if str(product_id).isdigit()]
    products = Product.objects.filter(id__in=product_ids, is_active=True)
    items = []
    total = 0
    for product in products:
        quantity = cart.get(str(product.id), 0)
        if not isinstance(quantity, int) or quantity <= 0:
            continue
        quantity = min(quantity, product.stock)
        if quantity == 0:
            continue
        line_total = product.price * quantity
        total += line_total
        items.append({'product': product, 'quantity': quantity, 'line_total': line_total})

    return items, total


@login_required
def checkout(request):
    items, subtotal = get_cart_items_and_total(request)
    if not items:
        return redirect('perfumery:cart')

    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            state = form.cleaned_data['state']
            lga = form.cleaned_data['lga']
            delivery_fee = lga.delivery_fee
            grand_total = subtotal + delivery_fee
            full_name = form.cleaned_data['full_name'].strip()
            name_parts = full_name.split(maxsplit=1)

            with transaction.atomic():
                profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
                profile.phone_number = form.cleaned_data['phone_number']
                profile.state = state
                profile.local_government = lga
                profile.city_area = form.cleaned_data['city_area']
                profile.delivery_address = form.cleaned_data['delivery_address']
                profile.save()

                request.user.first_name = name_parts[0] if name_parts else ''
                request.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
                request.user.save(update_fields=('first_name', 'last_name'))

            request.session['checkout'] = {
                'full_name': full_name,
                'email': form.cleaned_data['email'],
                'phone_number': form.cleaned_data['phone_number'],
                'state_id': state.pk,
                'lga_id': lga.pk,
                'lga_name': lga.name,
                'estimated_days': lga.estimated_days,
                'city_area': form.cleaned_data['city_area'],
                'delivery_address': form.cleaned_data['delivery_address'],
                'order_note': form.cleaned_data['order_note'],
                'subtotal': str(subtotal),
                'delivery_fee': str(delivery_fee),
                'grand_total': str(grand_total),
                'items': [
                    {
                        'name': item['product'].name,
                        'quantity': item['quantity'],
                        'unit_price': str(item['product'].price),
                        'line_total': str(item['line_total']),
                    }
                    for item in items
                ],
            }
            return redirect('perfumery:payment')
    else:
        form = CheckoutForm(user=request.user)

    return render(request, 'perfumery/checkout.html', {
        'form': form,
        'items': items,
        'subtotal': subtotal,
        'delivery_fee': Decimal('0.00'),
        'grand_total': subtotal,
    })


@login_required
def local_governments(request):
    state_id = request.GET.get('state_id')
    if not state_id or not state_id.isdigit() or not State.objects.filter(pk=state_id, is_active=True, code__in=NIGERIAN_LOCATIONS).exists():
        return JsonResponse({'error': 'Choose a valid state.'}, status=400)
    lgas = LocalGovernment.objects.filter(
        state_id=state_id,
        state__is_active=True,
        is_active=True,
    )
    return JsonResponse({'lgas': [{'id': lga.pk, 'name': lga.name} for lga in lgas]})


@login_required
def delivery_fee(request):
    lga_id = request.GET.get('lga_id')
    if not lga_id or not lga_id.isdigit():
        return JsonResponse({'error': 'Choose a valid local government.'}, status=400)
    lga = LocalGovernment.objects.filter(pk=lga_id, state__is_active=True, is_active=True).first()
    if not lga:
        return JsonResponse({'error': 'Choose a valid local government.'}, status=400)
    if lga.delivery_fee is None:
        return JsonResponse({'error': 'Delivery fee has not been configured for this area.'}, status=409)
    return JsonResponse({
        'delivery_fee': str(lga.delivery_fee),
        'estimated_days': lga.estimated_days,
    })


@login_required
def payment(request):
    checkout_data = request.session.get('checkout')
    if not checkout_data:
        return redirect('perfumery:checkout')
    lga = LocalGovernment.objects.filter(pk=checkout_data.get('lga_id')).select_related('state').first()
    return render(request, 'perfumery/payment.html', {
        'checkout': checkout_data,
        'lga': lga,
    })


def add_to_cart(request, product_id):
    if request.method != 'POST':
        return redirect('perfumery:product_list')
    product = get_object_or_404(Product, id=product_id, is_active=True)
    try:
        quantity = int(request.POST.get('quantity', '1'))
    except (TypeError, ValueError):
        quantity = 1
    quantity = max(quantity, 1)

    if product.stock <= 0:
        messages.error(request, 'This fragrance is currently out of stock.')
    else:
        cart = request.session.setdefault('cart', {})
        current_quantity = cart.get(str(product.id), 0)
        if not isinstance(current_quantity, int):
            current_quantity = 0
        cart[str(product.id)] = min(current_quantity + quantity, product.stock)
        request.session.modified = True
        messages.success(request, f'{product.name} added to your bag.')

    target = request.POST.get('next', '')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect('perfumery:cart')


def update_cart_item(request, product_id):
    if request.method != 'POST':
        return redirect('perfumery:cart')
    cart = request.session.get('cart', {})
    product = get_object_or_404(Product, id=product_id, is_active=True)
    try:
        quantity = int(request.POST.get('quantity', '1'))
    except (TypeError, ValueError):
        quantity = 1

    if not isinstance(cart, dict):
        cart = {}
    if quantity <= 0:
        cart.pop(str(product.id), None)
    elif product.stock <= 0:
        cart.pop(str(product.id), None)
        messages.error(request, f'{product.name} is out of stock and was removed.')
    else:
        cart[str(product.id)] = min(quantity, product.stock)
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('perfumery:cart')


def remove_cart_item(request, product_id):
    if request.method != 'POST':
        return redirect('perfumery:cart')
    cart = request.session.get('cart', {})
    if isinstance(cart, dict):
        cart.pop(str(product_id), None)
        request.session['cart'] = cart
        request.session.modified = True
    return redirect('perfumery:cart')
