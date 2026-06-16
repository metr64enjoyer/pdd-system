from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile, Organization, Event


class RegistrationForm(UserCreationForm):
    # ФИО поля
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Иванов",
                "autocomplete": "off",
            }
        ),
        label="Фамилия",
    )

    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Иван",
                "autocomplete": "off",
            }
        ),
        label="Имя",
    )

    patronymic = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Иванович",
                "autocomplete": "off",
            }
        ),
        label="Отчество",
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "example@mail.ru",
                "autocomplete": "off",
            }
        ),
    )

    username = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите логин",
                "autocomplete": "off",
            }
        ),
    )

    inn = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "id_inn",
                "placeholder": "10 или 12 цифр",
                "maxlength": "12",
                "autocomplete": "off",
            }
        ),
        label="ИНН организации",
    )

    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "+7 (XXX) XXX-XX-XX",
                "autocomplete": "off",
            }
        ),
        label="Контактный телефон",
    )

    position = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Например: Директор, Инспектор",
                "autocomplete": "off",
            }
        ),
        label="Ваша должность",
    )

    yuid_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Например: Светофор",
                "autocomplete": "off",
            }
        ),
        label="Название ЮИД-отряда",
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите пароль",
                "autocomplete": "new-password",
            }
        ),
        label="Пароль",
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Повторите пароль",
                "autocomplete": "new-password",
            }
        ),
        label="Подтверждение пароля",
    )

    class Meta:
        model = User
        fields = [
            "last_name",
            "first_name",
            "patronymic",
            "username",
            "email",
            "inn",
            "phone",
            "position",
            "yuid_name",
            "password1",
            "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email

    def clean_inn(self):
        inn = self.cleaned_data.get("inn")
        if not inn:
            raise forms.ValidationError("ИНН обязателен для регистрации")
        inn = inn.strip()
        if len(inn) not in [10, 12]:
            raise forms.ValidationError("ИНН должен содержать 10 или 12 цифр")
        if not inn.isdigit():
            raise forms.ValidationError("ИНН должен содержать только цифры")
        return inn

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.last_name = self.cleaned_data.get("last_name", "")
        user.first_name = self.cleaned_data.get("first_name", "")

        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.user_type = "organization"
            profile.phone = self.cleaned_data.get("phone", "")
            profile.position = self.cleaned_data.get("position", "")
            profile.patronymic = self.cleaned_data.get("patronymic", "")
            profile.yuid_name = self.cleaned_data.get("yuid_name", "")

            inn = self.cleaned_data.get("inn")
            org = Organization.objects.filter(inn=inn).first()
            if not org:
                org = Organization.objects.create(
                    inn=inn, name=f"Организация {inn}", is_active=True
                )
            profile.organization = org
            profile.save()

        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Логин",
                "autocomplete": "off",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Пароль",
                "autocomplete": "off",
            }
        )
    )


class EventForm(forms.ModelForm):
    class Meta:
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            from .models import Event
            # Собираем все существующие теги
            all_tags = set()
            for event in Event.objects.exclude(tags__isnull=True).exclude(tags=''):
                for tag in event.tags.split(','):
                    tag = tag.strip()
                    if tag:
                        all_tags.add(tag)
            if all_tags:
                self.fields['tags'].widget.attrs['data-tags'] = ', '.join(sorted(all_tags))
        model = Event
        fields = [
            "title",
            "date",
            "time",
            "status",
            "event_type",
            "location_type",
            "location_address",
            "latitude",
            "longitude",
            "description",
            "report_link",
            "tags",
            "responsible_person",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Введите название"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "status": forms.Select(attrs={"class": "form-select"}, choices=[
                ('planned', 'Запланировано'),
                ('conducted', 'Проведено'),
                ('cancelled', 'Отменено'),
                ('approved', 'Подтверждено'),
            ]),
            "event_type": forms.Select(attrs={"class": "form-select"}),
            "location_type": forms.Select(attrs={"class": "form-select"}),
            "location_address": forms.TextInput(attrs={"class": "form-control", "placeholder": "Адрес или место проведения"}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Описание мероприятия"}),
            "report_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "tags": forms.TextInput(attrs={"class": "form-control", "placeholder": "светофор, дети, школа", "id": "id_tags"}),
            "responsible_person": forms.TextInput(attrs={"class": "form-control", "placeholder": "Иванов И.И."}),
            "district": forms.TextInput(attrs={"class": "form-control", "id": "id_district"}),
        }