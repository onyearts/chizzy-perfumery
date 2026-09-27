from django.urls import path

from . import views

app_name = 'perfumery'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('search/', views.search_products, name='search'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
    path('cart/', views.cart_detail, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('local-governments/', views.local_governments, name='local_governments'),
    path('delivery-fee/', views.delivery_fee, name='delivery_fee'),
    path('payment/', views.payment, name='payment'),
    path('payment/initialize/', views.payment_initialize, name='payment_initialize'),
    path('account/', views.account_dashboard, name='account_dashboard'),
    path('account/delivery-address/', views.account_delivery_address, name='account_delivery_address'),
    path('account/settings/', views.account_settings, name='account_settings'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:product_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
]
