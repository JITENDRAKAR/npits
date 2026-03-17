from django import forms
from .models import Portfolio, Profile
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(max_length=100, required=True, label='Name')
    email = forms.EmailField(required=True, label='Email ID')
    mobile_number = forms.CharField(max_length=15, required=True, label='Mobile Number')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('full_name', 'email', 'mobile_number')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(username=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. '
                'Please login or reset your password if you forgot it.'
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = user.email  # Set username to email
        if commit:
            user.save()
            # Handle Name and Mobile via Profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.full_name = self.cleaned_data['full_name']
            profile.mobile_number = self.cleaned_data['mobile_number']
            profile.save()
        return user

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'mobile_number', 'date_of_birth', 'gender', 'investor_type']
        labels = {
            'full_name': 'Name',
            'mobile_number': 'Mobile Number',
            'date_of_birth': 'Date of Birth',
            'gender': 'Gender',
            'investor_type': 'Investor Type: Initial investment per stock/ETF accordingly.',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter mobile number'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'investor_type': forms.Select(attrs={'class': 'form-control'}),
        }

class EmailOrMobileAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Mobile Number or Email', widget=forms.TextInput(attrs={'autofocus': True, 'class': 'form-control', 'placeholder': 'Enter Mobile Number or Email'}))


class UploadFileForm(forms.Form):
    file = forms.FileField(label="Select CSV/Excel File")

class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['quantity', 'avg_cost']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Quantity'}),
            'avg_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter Avg. Cost'}),
        }

class ManualPortfolioForm(forms.Form):
    company_name = forms.CharField(
        label='COMPANY NAME',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Search company name...',
            'id': 'id_company_name',
            'autocomplete': 'off'
        })
    )
    symbol = forms.CharField(
        label='STOCK SYMBOL (AUTO-FILLED)',
        max_length=20, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Symbol will auto-fill',
            'id': 'id_symbol',
            'readonly': 'readonly'
        })
    )
    quantity = forms.IntegerField(
        label='QUANTITY',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Quantity'})
    )
    avg_cost = forms.DecimalField(
        label='AVERAGE COST (?)',
        max_digits=10, 
        decimal_places=2, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter Avg. Cost'})
    )
    date = forms.DateField(
        label='PURCHASE DATE',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

class EditLotForm(forms.Form):
    quantity = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity'})
    )
    price = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Price'})
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your registered email'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No user found with this email address.")
        return email

class VerifyOTPForm(forms.Form):
    otp = forms.CharField(
        label='6-Digit Code',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 6-digit code'})
    )

class SetPasswordForm(forms.Form):
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'})
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data
