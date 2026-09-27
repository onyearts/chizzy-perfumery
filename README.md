# Chizzy Perfumery

A Django storefront for perfume sellers. Prices are displayed in Nigerian naira (NGN). The catalog uses reusable categories and products so other product types can be added later. Product search includes close matches, the shopping bag tracks items in the session, and customer accounts use email verification. Payment checkout is not included yet.

## Setup

Python 3.10 or newer is recommended.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/` for the storefront or `http://127.0.0.1:8000/admin/` to manage categories and products. Add products through the Django admin; active products appear in the public catalog. Product photos can be selected from your device in the image upload field and are stored under `media/products/` during development.

## Customer accounts and social sign-in

Email/password signup, login, logout, email verification, and password reset are handled by django-allauth. When SMTP is configured below, verification and password-reset messages are delivered to the customer's email address. Without SMTP settings, the development fallback prints those messages in the server terminal.

### Enable real email delivery

Run `Copy-Item .env.example .env` in PowerShell, then configure `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` or `EMAIL_USE_SSL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` in `.env`. SMTP activates automatically when the host, username, and password are all present. Restart Django after editing `.env`.

For Gmail, use `smtp.gmail.com`, port `587`, and TLS. `EMAIL_HOST_USER` should be your sending Gmail address, `EMAIL_HOST_PASSWORD` should be a Google App Password (not your normal Google password), and `DEFAULT_FROM_EMAIL` should be that same authorized sender address. Other SMTP mail providers can use their own host, port, and TLS/SSL settings. Keep `.env` private; never paste mail credentials into chat or commit them.

To check which backend Django selected, run:

```powershell
python manage.py shell -c "from django.conf import settings; print(settings.EMAIL_BACKEND)"
```

Run `Copy-Item .env.example .env` in PowerShell, then fill in the Google and/or Facebook provider credentials in `.env` to enable social sign-in. Restart Django after changing it. `.env` is ignored by Git. Never commit provider secrets or place them in templates or browser JavaScript.

Register this Google OAuth callback URL for local development:

```text
http://localhost:8000/accounts/google/login/callback/
```

For Facebook, create a Facebook Login app, configure its website domain as `localhost`, and register this OAuth callback URL:

```text
http://localhost:8000/accounts/facebook/login/callback/
```

Facebook sign-in requests the `email` and `public_profile` permissions. Google and Facebook social identities are stored by django-allauth using its default social account models.

## Tests

```powershell
python manage.py test
```