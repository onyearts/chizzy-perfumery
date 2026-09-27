from django import forms
from django.core.exceptions import ValidationError

from .locations import NIGERIAN_LOCATIONS
from .models import CustomerProfile, LocalGovernment, State


class CheckoutForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        label='Full name',
        widget=forms.TextInput(attrs={
            'class': 'form-control checkout-input',
            'autocomplete': 'name',
            'placeholder': 'Name for delivery',
        }),
    )
    email = forms.EmailField(
        label='Email address',
        disabled=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control checkout-input',
            'autocomplete': 'email',
        }),
    )
    phone_number = forms.CharField(
        max_length=32,
        label='Phone number',
        widget=forms.TextInput(attrs={
            'class': 'form-control checkout-input',
            'autocomplete': 'tel',
            'inputmode': 'tel',
            'placeholder': 'Number for delivery updates',
        }),
    )
    state = forms.ModelChoiceField(
        queryset=State.objects.none(),
        empty_label='Choose a state',
        label='State',
        widget=forms.Select(attrs={
            'class': 'form-select checkout-input',
            'autocomplete': 'address-level1',
        }),
    )
    lga = forms.ModelChoiceField(
        queryset=LocalGovernment.objects.none(),
        empty_label='Choose a local government',
        label='Local Government',
        widget=forms.Select(attrs={
            'class': 'form-select checkout-input',
            'autocomplete': 'address-level2',
            'disabled': True,
        }),
    )
    city_area = forms.CharField(
        max_length=120,
        label='City / area',
        widget=forms.TextInput(attrs={
            'class': 'form-control checkout-input',
            'autocomplete': 'address-level2',
            'placeholder': 'City or local area',
        }),
    )
    delivery_address = forms.CharField(
        max_length=500,
        label='Full delivery address',
        widget=forms.Textarea(attrs={
            'class': 'form-control checkout-input',
            'autocomplete': 'street-address',
            'rows': 3,
            'placeholder': 'House number, street, landmark, and other delivery details',
        }),
    )
    order_note = forms.CharField(
        max_length=1000,
        required=False,
        label='Order note (optional)',
        widget=forms.Textarea(attrs={
            'class': 'form-control checkout-input',
            'rows': 2,
            'placeholder': 'Anything the delivery team should know?',
        }),
    )

    def __init__(self, *args, user, **kwargs):
        initial = kwargs.setdefault('initial', {})
        profile = CustomerProfile.objects.filter(user=user).select_related('state', 'local_government').first()
        full_name = user.get_full_name().strip() or user.get_username()
        initial.setdefault('full_name', full_name)
        initial.setdefault('email', user.email)
        initial.setdefault(
            'phone_number',
            (profile.phone_number if profile and profile.phone_number else self._user_phone(user)),
        )
        if profile:
            initial.setdefault('city_area', profile.city_area)
            initial.setdefault('delivery_address', profile.delivery_address)
            if profile.state_id and State.objects.filter(
                pk=profile.state_id,
                is_active=True,
                code__in=NIGERIAN_LOCATIONS,
            ).exists():
                initial.setdefault('state', profile.state_id)

        super().__init__(*args, **kwargs)
        self.fields['state'].queryset = State.objects.filter(is_active=True, code__in=NIGERIAN_LOCATIONS)
        state_id = self.data.get(self.add_prefix('state')) if self.is_bound else None
        if not self.is_bound and profile and profile.state_id:
            state_id = profile.state_id

        if state_id and str(state_id).isdigit():
            state = self.fields['state'].queryset.filter(pk=state_id).first()
        else:
            state = None

        if state:
            self.fields['lga'].queryset = LocalGovernment.objects.filter(
                state=state,
                state__is_active=True,
                is_active=True,
            )
            self.fields['lga'].widget.attrs.pop('disabled', None)
            if (
                not self.is_bound
                and profile
                and profile.local_government_id
                and profile.local_government.state_id == state.pk
                and profile.local_government.is_active
            ):
                self.initial['lga'] = profile.local_government_id

    def clean_lga(self):
        lga = self.cleaned_data['lga']
        if lga.delivery_fee is None:
            raise ValidationError('Delivery is not available for this area yet. Please choose another area.')
        return lga

    @staticmethod
    def _user_phone(user):
        for field_name in ('phone', 'phone_number', 'mobile_number'):
            value = getattr(user, field_name, '')
            if value:
                return str(value)
        return ''


class CustomerAddressForm(forms.ModelForm):
    state = forms.ModelChoiceField(
        queryset=State.objects.none(),
        empty_label='Choose a state',
        widget=forms.Select(attrs={'class': 'form-select checkout-input'}),
    )
    local_government = forms.ModelChoiceField(
        queryset=LocalGovernment.objects.none(),
        empty_label='Choose a local government',
        widget=forms.Select(attrs={
            'class': 'form-select checkout-input',
            'disabled': True,
        }),
    )

    class Meta:
        model = CustomerProfile
        fields = ('phone_number', 'state', 'local_government', 'city_area', 'delivery_address')
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control checkout-input',
                'autocomplete': 'tel',
                'inputmode': 'tel',
            }),
            'city_area': forms.TextInput(attrs={
                'class': 'form-control checkout-input',
                'autocomplete': 'address-level2',
            }),
            'delivery_address': forms.Textarea(attrs={
                'class': 'form-control checkout-input',
                'autocomplete': 'street-address',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['state'].queryset = State.objects.filter(
            is_active=True,
            code__in=NIGERIAN_LOCATIONS,
        )
        state_id = self.data.get(self.add_prefix('state')) if self.is_bound else self.instance.state_id
        if state_id and str(state_id).isdigit():
            state = self.fields['state'].queryset.filter(pk=state_id).first()
        else:
            state = None

        if state:
            self.fields['local_government'].queryset = LocalGovernment.objects.filter(
                state=state,
                state__is_active=True,
                is_active=True,
            )
            self.fields['local_government'].widget.attrs.pop('disabled', None)

    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get('state')
        local_government = cleaned_data.get('local_government')
        if state and local_government and local_government.state_id != state.pk:
            self.add_error('local_government', 'Choose a local government in the selected state.')
        return cleaned_data


class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ('profile_picture',)
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control profile-picture-input',
                'accept': 'image/*',
            }),
        }
