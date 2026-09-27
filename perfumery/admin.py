from django.contrib import admin
from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse
from .locations import NIGERIAN_LOCATIONS
from .models import Category, CustomerProfile, LocalGovernment, Order, OrderItem, Payment, Product, State


class StateAdminForm(forms.ModelForm):
	class Meta:
		model = State
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['code'].required = True
		self.fields['code'].choices = [('', 'Choose a state')] + [
			(code, name) for code, (name, _lgas) in NIGERIAN_LOCATIONS.items()
		]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'slug')
	prepopulated_fields = {'slug': ('name',)}
	search_fields = ('name',)


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
	form = StateAdminForm
	list_display = ('code', 'name', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('name', 'code')
	list_editable = ('is_active',)
	fields = ('code', 'name', 'is_active')
	readonly_fields = ('name',)

	def get_readonly_fields(self, request, obj=None):
		readonly = list(super().get_readonly_fields(request, obj))
		if obj and obj.code:
			readonly.append('code')
		return readonly

	def _lga_admin_url(self, obj):
		url = reverse('admin:perfumery_localgovernment_changelist')
		return f'{url}?state__id__exact={obj.pk}'

	def response_add(self, request, obj, post_url_continue=None):
		return HttpResponseRedirect(self._lga_admin_url(obj))

	def response_change(self, request, obj):
		return HttpResponseRedirect(self._lga_admin_url(obj))


@admin.register(LocalGovernment)
class LocalGovernmentAdmin(admin.ModelAdmin):
	list_display = ('state', 'name', 'delivery_fee', 'fee_status', 'is_active')
	list_filter = ('state', 'is_active')
	list_editable = ('delivery_fee', 'is_active')
	search_fields = ('name', 'state__name')
	list_select_related = ('state',)
	readonly_fields = ('state', 'name')

	@admin.display(description='Fee configured')
	def fee_status(self, obj):
		return 'Yes' if obj.delivery_fee is not None else 'Not configured'

	def has_add_permission(self, request):
		return False


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'phone_number', 'state', 'local_government', 'city_area')
	list_filter = ('state', 'local_government')
	search_fields = ('user__username', 'user__email', 'phone_number', 'city_area', 'delivery_address')
	list_select_related = ('user', 'state', 'local_government')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('name', 'brand', 'category', 'volume_ml', 'price', 'stock', 'is_active')
	list_filter = ('is_active', 'category')
	list_editable = ('volume_ml', 'price', 'stock', 'is_active')
	prepopulated_fields = {'slug': ('name',)}
	search_fields = ('name', 'brand', 'description')


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	can_delete = False
	readonly_fields = ('product', 'quantity', 'price_at_purchase')

	def has_add_permission(self, request, obj=None):
		return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('order_number', 'customer', 'full_name', 'grand_total', 'status', 'created_at')
	list_filter = ('status', 'state', 'local_government', 'created_at')
	search_fields = ('full_name', 'email', 'customer__email')
	date_hierarchy = 'created_at'
	list_select_related = ('customer', 'state', 'local_government')
	readonly_fields = ('order_number', 'customer', 'subtotal', 'delivery_fee', 'grand_total', 'created_at')
	inlines = (OrderItemInline,)
	ordering = ('-created_at',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = ('product', 'order', 'quantity', 'price_at_purchase')
	list_filter = ('order__status',)
	search_fields = ('product__name', 'order__customer__email')
	list_select_related = ('product', 'order', 'order__customer')
	readonly_fields = ('order', 'product', 'quantity', 'price_at_purchase')

	def has_add_permission(self, request):
		return False

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = ('reference', 'order', 'amount', 'provider', 'status', 'paid_at', 'created_at')
	list_filter = ('provider', 'status', 'paid_at', 'created_at')
	search_fields = ('reference', 'order__customer__email')
	date_hierarchy = 'created_at'
	list_select_related = ('order', 'order__customer')
	readonly_fields = (
		'order', 'reference', 'amount', 'provider', 'status', 'paid_at',
		'gateway_response', 'created_at',
	)

	def has_add_permission(self, request):
		return False

	def has_delete_permission(self, request, obj=None):
		return False
