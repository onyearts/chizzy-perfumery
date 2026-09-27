from decimal import Decimal
from urllib.parse import urlsplit

from django.core import mail
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from allauth.account.models import EmailAddress, EmailConfirmationHMAC

from .models import Category, Product


class CatalogTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Eau de parfum')
		self.product = Product.objects.create(
			category=self.category,
			name='Cedar No. 4',
			brand='Maison Example',
			price=Decimal('84.00'),
			stock=5,
			description='Warm cedar and citrus.',
		)

	def test_slugs_are_generated_and_detail_url_resolves(self):
		self.assertEqual(self.category.slug, 'eau-de-parfum')
		self.assertEqual(self.product.slug, 'cedar-no-4')
		self.assertEqual(self.product.get_absolute_url(), '/products/cedar-no-4/')

	def test_catalog_shows_active_products(self):
		response = self.client.get(reverse('perfumery:product_list'))
		self.assertContains(response, 'Cedar No. 4')
		self.assertContains(response, '₦84.00')

	def test_inactive_products_are_hidden(self):
		self.product.is_active = False
		self.product.save()
		response = self.client.get(reverse('perfumery:product_list'))
		self.assertNotContains(response, 'Cedar No. 4')

	def test_product_detail_shows_description_and_price(self):
		response = self.client.get(self.product.get_absolute_url())
		self.assertContains(response, 'Warm cedar and citrus.')
		self.assertContains(response, '₦84.00')

	def test_zero_stock_shows_out_of_stock_and_disables_purchase(self):
		self.product.stock = 0
		self.product.save()

		response = self.client.get(self.product.get_absolute_url())

		self.assertContains(response, 'Out of Stock')
		self.assertContains(response, 'stock-note--out')
		self.assertContains(response, 'class="btn btn-signup auth-submit" type="submit" disabled')

	def test_limited_stock_shows_remaining_quantity(self):
		self.product.stock = 5
		self.product.save()

		response = self.client.get(self.product.get_absolute_url())

		self.assertContains(response, 'Limited Availability &mdash; Only 5 left')
		self.assertContains(response, 'stock-note--limited')
		self.assertNotContains(response, 'type="submit" disabled')

	def test_stock_above_ten_shows_in_stock(self):
		self.product.stock = 11
		self.product.save()

		response = self.client.get(self.product.get_absolute_url())

		self.assertContains(response, 'In Stock')
		self.assertContains(response, 'stock-note--available')

	def test_large_prices_use_thousands_separators(self):
		self.product.price = Decimal('125000.00')
		self.product.save()

		catalog_response = self.client.get(reverse('perfumery:product_list'))
		detail_response = self.client.get(self.product.get_absolute_url())

		self.assertContains(catalog_response, '₦125,000.00')
		self.assertContains(detail_response, '₦125,000.00')

	def test_search_suggests_close_matches_for_misspelled_query(self):
		response = self.client.get(reverse('perfumery:search_suggestions'), {'q': 'Ceder No 4'})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['suggestions'][0]['name'], 'Cedar No. 4')

	def test_search_results_keep_near_matches_for_typo(self):
		response = self.client.get(reverse('perfumery:search'), {'q': 'Ceder No 4'})

		self.assertContains(response, 'No exact match. Try these instead')
		self.assertContains(response, 'Cedar No. 4')
		self.assertContains(response, 'value="Ceder No 4"')

	def test_cart_add_update_and_remove(self):
		add_url = reverse('perfumery:add_to_cart', args=[self.product.id])
		update_url = reverse('perfumery:update_cart_item', args=[self.product.id])
		remove_url = reverse('perfumery:remove_cart_item', args=[self.product.id])

		self.client.post(add_url, {'quantity': '2'})
		response = self.client.get(reverse('perfumery:cart'))
		self.assertContains(response, '₦168.00')
		self.assertEqual(self.client.session['cart'][str(self.product.id)], 2)

		self.client.post(update_url, {'quantity': '3'})
		response = self.client.get(reverse('perfumery:cart'))
		self.assertContains(response, '₦252.00')

		self.client.post(remove_url)
		response = self.client.get(reverse('perfumery:cart'))
		self.assertContains(response, 'Your bag is waiting.')

	def test_admin_product_form_has_local_image_upload(self):
		admin_user = get_user_model().objects.create_superuser(
			username='catalog-admin',
			email='admin@example.com',
			password='test-password-123',
		)
		self.client.force_login(admin_user)

		response = self.client.get(reverse('admin:perfumery_product_add'))

		self.assertContains(response, 'name="image"')
		self.assertContains(response, 'type="file"')
		self.assertContains(response, 'Select media from your device.')
		self.assertContains(response, 'Enter the price in Nigerian naira (NGN).')

	def test_verified_user_can_log_in_and_log_out_with_email(self):
		user = get_user_model().objects.create_user(
			username='verified-customer',
			email='verified@example.com',
			password='Strong-Password-2026',
		)
		EmailAddress.objects.create(
			user=user,
			email=user.email,
			verified=True,
			primary=True,
		)

		login_response = self.client.post(reverse('account_login'), {
			'login': user.email,
			'password': 'Strong-Password-2026',
		})
		self.assertRedirects(login_response, reverse('perfumery:product_list'))
		self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

		logout_response = self.client.post(reverse('account_logout'))
		self.assertRedirects(logout_response, reverse('perfumery:product_list'))
		self.assertNotIn('_auth_user_id', self.client.session)

	@override_settings(SOCIALACCOUNT_PROVIDERS={
		'google': {'APPS': []},
		'facebook': {'APPS': []},
	})
	def test_account_entry_pages_render(self):
		login_response = self.client.get(reverse('account_login'))
		signup_response = self.client.get(reverse('account_signup'))
		self.assertContains(login_response, 'Log in')
		self.assertContains(signup_response, 'Create your account')
		for response in (login_response, signup_response):
			self.assertContains(response, 'Google')
			self.assertContains(response, 'Facebook')
			self.assertContains(response, 'Social sign-in buttons become active')
		self.assertContains(response, 'disabled')
		self.assertContains(self.client.get(reverse('account_reset_password')), 'Reset your password')

	@override_settings(SOCIALACCOUNT_PROVIDERS={
		'google': {'APPS': [{'client_id': 'test-google-client', 'secret': 'test-google-secret', 'key': ''}]},
		'facebook': {'APPS': [{'client_id': 'test-facebook-client', 'secret': 'test-facebook-secret', 'key': ''}]},
	})
	def test_configured_social_providers_show_login_links(self):
		response = self.client.get(reverse('account_login'))

		self.assertContains(response, 'Google')
		self.assertContains(response, 'Facebook')
		self.assertContains(response, '/accounts/google/login/')
		self.assertContains(response, '/accounts/facebook/login/')

	@override_settings(SOCIALACCOUNT_PROVIDERS={
		'google': {'APPS': [{'client_id': 'test-google-client', 'secret': 'test-google-secret', 'key': ''}]},
		'facebook': {'APPS': [{'client_id': 'test-facebook-client', 'secret': 'test-facebook-secret', 'key': ''}]},
	})
	def test_social_provider_handoff_pages_use_branded_confirmation(self):
		for provider in ('google', 'facebook'):
			response = self.client.get(f'/accounts/{provider}/login/?process=login')
			self.assertEqual(response.status_code, 200)
			self.assertContains(response, f'Continue with {provider.title()}')
			self.assertContains(response, 'Continue securely')
			self.assertContains(response, 'csrfmiddlewaretoken')
			self.assertContains(response, 'Return to the shop')

	@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
	def test_signup_confirmation_verifies_email_and_logs_user_in(self):
		response = self.client.post(reverse('account_signup'), {
			'username': 'new-customer',
			'email': 'new@example.com',
			'password1': 'Strong-Password-2026',
			'password2': 'Strong-Password-2026',
		})

		self.assertEqual(response.status_code, 302)
		user = get_user_model().objects.get(username='new-customer')
		email_address = EmailAddress.objects.get(user=user, email=user.email)
		self.assertFalse(email_address.verified)
		self.assertEqual(len(mail.outbox), 1)
		self.assertEqual(mail.outbox[0].subject, '[Chizzy Perfumery] Confirm your email address')
		self.assertIn('Thanks for creating an account with Chizzy Perfumery.', mail.outbox[0].body)
		self.assertIn('Verify your email address:', mail.outbox[0].body)
		self.assertNotIn('Hello from', mail.outbox[0].body)
		self.assertNotIn('localhost', mail.outbox[0].body)
		self.assertEqual(len(mail.outbox[0].alternatives), 1)
		self.assertIn('Verify email address', mail.outbox[0].alternatives[0][0])

		confirmation_url = reverse(
			'account_confirm_email',
			args=[EmailConfirmationHMAC(email_address).key],
		)
		confirm_page = self.client.get(confirmation_url)
		self.assertContains(confirm_page, 'Confirm your email')
		confirmation_response = self.client.post(confirmation_url)

		email_address.refresh_from_db()
		self.assertTrue(email_address.verified)
		self.assertRedirects(confirmation_response, reverse('perfumery:product_list'))
		self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

	@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
	def test_password_reset_email_updates_password_and_allows_login(self):
		user = get_user_model().objects.create_user(
			username='reset-customer',
			email='reset@example.com',
			password='Old-Password-2026',
		)
		EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)

		reset_response = self.client.post(reverse('account_reset_password'), {'email': user.email})
		self.assertRedirects(reset_response, reverse('account_reset_password_done'))
		self.assertEqual(len(mail.outbox), 1)
		reset_url = next(
			part for part in mail.outbox[0].body.split()
			if '/accounts/password/reset/key/' in part
		)
		reset_path = urlsplit(reset_url).path

		reset_page = self.client.get(reset_path, follow=True)
		self.assertContains(reset_page, 'Choose a new password')
		change_response = self.client.post(reset_page.request['PATH_INFO'], {
			'password1': 'New-Password-2026',
			'password2': 'New-Password-2026',
		})
		self.assertEqual(change_response.status_code, 302)

		login_response = self.client.post(reverse('account_login'), {
			'login': user.email,
			'password': 'New-Password-2026',
		})
		self.assertRedirects(login_response, reverse('perfumery:product_list'))
