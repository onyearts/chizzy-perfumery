import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db import transaction
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify

from .locations import NIGERIAN_LOCATIONS


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


STATE_CHOICES = tuple((code, name) for code, (name, _lgas) in NIGERIAN_LOCATIONS.items())
STATE_NAMES = {code: name for code, (name, _lgas) in NIGERIAN_LOCATIONS.items()}
NIGERIAN_LOCAL_GOVERNMENTS = {code: lgas for code, (_name, lgas) in NIGERIAN_LOCATIONS.items()}


class State(models.Model):
    code = models.CharField(max_length=2, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100, unique=True, editable=False)
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name or self.code or 'Unconfigured state'

    def save(self, *args, **kwargs):
        if self.code in STATE_NAMES:
            self.name = STATE_NAMES[self.code]
        using = kwargs.get('using') or self._state.db or 'default'
        with transaction.atomic(using=using):
            super().save(*args, **kwargs)
            if self.code in NIGERIAN_LOCAL_GOVERNMENTS:
                LocalGovernment.objects.using(using).bulk_create(
                    [LocalGovernment(state=self, name=name) for name in NIGERIAN_LOCAL_GOVERNMENTS[self.code]],
                    ignore_conflicts=True,
                )


class LocalGovernment(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='lgas')
    name = models.CharField(max_length=100)
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=3000,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Delivery fee in Nigerian naira (NGN).',
    )
    estimated_days = models.CharField(max_length=40, default='1–3 business days')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['state', 'name'], name='unique_lga_name_per_state'),
        ]
        verbose_name = 'local government'
        verbose_name_plural = 'local governments'

    def __str__(self):
        return f'{self.name}, {self.state.name}'


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_profile',
    )
    profile_picture = models.ImageField(upload_to='profiles/', blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_profiles',
    )
    local_government = models.ForeignKey(
        LocalGovernment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_profiles',
    )
    city_area = models.CharField(max_length=120, blank=True)
    delivery_address = models.TextField(blank=True)

    def __str__(self):
        return f'Shipping profile for {self.user}'


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='products',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    brand = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Enter the price in Nigerian naira (NGN).',
    )
    volume_ml = models.PositiveIntegerField(
        default=100,
        help_text='Bottle size in millilitres (ml).',
    )
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        help_text='Select media from your device.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('perfumery:product_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending payment'
        PAID = 'PAID', 'Paid'
        PROCESSING = 'PROCESSING', 'Processing'
        SHIPPED = 'SHIPPED', 'Shipped'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='perfumery_orders',
    )
    order_number = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    full_name = models.CharField(max_length=160)
    email = models.EmailField(max_length=254)
    phone_number = models.CharField(max_length=30)
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name='orders')
    local_government = models.ForeignKey(
        LocalGovernment,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    city_area = models.CharField(max_length=120)
    delivery_address = models.TextField()
    order_note = models.TextField(blank=True)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return str(self.order_number)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_at_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} × {self.product.name} ({self.order.order_number})'


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    provider = models.CharField(max_length=20, default='paystack')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference
