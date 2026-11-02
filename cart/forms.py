from django import forms
from .models import Order


PRODUCT_QUANTITY_CHOICES = [(i, str(i)) for i in range(1, 21)]


class CartAddProductForm(forms.Form):
    quantity = forms.TypedChoiceField(
        choices=PRODUCT_QUANTITY_CHOICES,
        coerce=int,
        initial=1,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    update = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput
    )


class PromoCodeApplyForm(forms.Form):
    code = forms.CharField(
        max_length=50,
        label='Promotional Code',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter promo code (e.g. PCSHOP10)',
            'class': 'form-control mono'
        })
    )


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'city',
            'postal_code',
            'payment_method',
            'notes',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com', 'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'placeholder': '+998 90 123 45 67', 'class': 'form-control'}),
            'address': forms.TextInput(attrs={'placeholder': 'Street address, apartment, building', 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'placeholder': 'Tashkent', 'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'placeholder': '100000', 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Delivery instructions or notes (optional)', 'class': 'form-control'}),
        }
