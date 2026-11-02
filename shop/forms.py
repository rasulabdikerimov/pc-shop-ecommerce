from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.text import slugify
from .models import User, Category, Brand, Product, Discount, Review
from cart.models import PromoCode, Order


class UserCreationFormByMe(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Email Address',
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com', 'class': 'form-control'})
    )
    first_name = forms.CharField(
        required=False,
        max_length=150,
        label='First Name',
        widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control'})
    )
    last_name = forms.CharField(
        required=False,
        max_length=150,
        label='Last Name',
        widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control'})
    )
    phone_num = forms.CharField(
        required=False,
        max_length=30,
        label='Phone Number',
        widget=forms.TextInput(attrs={'placeholder': '+998 90 123 45 67', 'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'phone_num',
            'image',
        ]

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError("An email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address is already registered.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username


class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='Email Address')

    class Meta:
        model = User
        fields = [
            'image',
            'first_name',
            'last_name',
            'username',
            'email',
            'phone_num',
            'address',
            'city',
            'postal_code',
            'bio',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us about your PC setup...'}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email address is already in use by another account.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username


class ReviewForm(forms.ModelForm):
    title = forms.CharField(
        label='Review Title',
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Summarize your experience', 'class': 'form-control'})
    )
    rating = forms.TypedChoiceField(
        label='Rating',
        choices=Review.RATING_CHOICES,
        coerce=int,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    body = forms.CharField(
        label='Detailed Review',
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'What did you like or dislike about this hardware?', 'class': 'form-control'})
    )

    class Meta:
        model = Review
        fields = ['title', 'rating', 'body']


class AdminProductForm(forms.ModelForm):
    slug = forms.CharField(
        required=False,
        max_length=150,
        help_text="Leave blank to auto-generate from product name."
    )

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'sku', 'category', 'brand', 'price', 'original_price',
            'discount_percent', 'stock', 'available', 'is_featured',
            'short_specs', 'description', 'specifications', 'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'specifications': forms.Textarea(attrs={'rows': 5, 'placeholder': 'GPU: RTX 4070 Super\nMemory: 12GB GDDR6X'}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip()
        name = self.cleaned_data.get('name') or ''
        if not slug and name:
            slug = slugify(name)
        if not slug:
            raise forms.ValidationError("Product slug is required.")
        qs = Product.objects.filter(slug=slug).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A product with this slug already exists.")
        return slug


class AdminCategoryForm(forms.ModelForm):
    slug = forms.SlugField(required=False, max_length=100)

    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'icon', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip()
        name = self.cleaned_data.get('name') or ''
        if not slug and name:
            slug = slugify(name)
        qs = Category.objects.filter(slug=slug).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A category with this slug already exists.")
        return slug


class AdminBrandForm(forms.ModelForm):
    slug = forms.SlugField(required=False, max_length=100)

    class Meta:
        model = Brand
        fields = ['name', 'slug', 'description', 'logo', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip()
        name = self.cleaned_data.get('name') or ''
        if not slug and name:
            slug = slugify(name)
        qs = Brand.objects.filter(slug=slug).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A brand with this slug already exists.")
        return slug


class AdminDiscountForm(forms.ModelForm):
    class Meta:
        model = Discount
        fields = [
            'name', 'description', 'discount_type', 'value',
            'products', 'categories', 'start_date', 'end_date', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }


class AdminPromoCodeForm(forms.ModelForm):
    class Meta:
        model = PromoCode
        fields = [
            'code', 'description', 'discount_type', 'discount_value',
            'min_order_amount', 'usage_limit', 'valid_from', 'valid_until', 'is_active'
        ]
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'valid_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }


class AdminOrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'payment_status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
