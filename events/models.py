from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Organization(models.Model):
    name = models.CharField("Название", max_length=300)
    inn = models.CharField("ИНН", max_length=12, unique=True)
    ogrn = models.CharField("ОГРН", max_length=15, blank=True, null=True)
    kpp = models.CharField("КПП", max_length=9, blank=True, null=True)
    address = models.TextField("Адрес", blank=True, null=True)
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True)
    latitude = models.FloatField("Широта", blank=True, null=True)
    longitude = models.FloatField("Долгота", blank=True, null=True)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    district = models.CharField('Район', max_length=100, blank=True, null=True)
    latitude = models.FloatField("Широта", blank=True, null=True)
    longitude = models.FloatField("Долгота", blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Организация"
        verbose_name_plural = "Организации"
        ordering = ["name"]


class UserProfile(models.Model):
    USER_TYPES = [
        ("organization", "Представитель организации"),
        ("propaganda", "Сотрудник пропаганды"),
        ("admin", "Администратор"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    user_type = models.CharField(
        max_length=20, choices=USER_TYPES, default="organization"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Организация",
    )
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)
    position = models.CharField("Должность", max_length=100, blank=True, null=True)
    patronymic = models.CharField("Отчество", max_length=100, blank=True, null=True)
    yuid_name = models.CharField(
        "Название ЮИД-отряда", max_length=200, blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user_type == "propaganda":
            return f"{self.user.username} - Пропаганда"
        return f"{self.user.username} - {self.organization.name if self.organization else 'Без организации'}"

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

from django.db.models.signals import post_delete
from django.dispatch import receiver

@receiver(post_delete, sender=User)
def delete_organization_with_user(sender, instance, **kwargs):
    """При удалении пользователя удаляем его организацию, если она не привязана к другим"""
    try:
        profile = instance.profile
        if profile.organization:
            org = profile.organization
            # Проверяем, есть ли другие пользователи у этой организации
            other_users = UserProfile.objects.filter(organization=org).exclude(user=instance).count()
            if other_users == 0:
                org.delete()
    except UserProfile.DoesNotExist:
        pass

class Event(models.Model):
    STATUS_CHOICES = [
        ("planned", "Запланировано"),
        ("conducted", "Проведено"),
        ("cancelled", "Отменено"),
        ("approved", "Подтверждено"),
    ]

    EVENT_TYPES = [
        ("lecture", "Лекция / Беседа"),
        ("practical", "Практическое занятие"),
        ("quiz", "Викторина / Конкурс"),
        ("parent_meeting", "Родительское собрание"),
        ("briefing", "Инструктаж"),
        ("action", "Акция / Рейд"),
        ("excursion", "Экскурсия"),
        ("training", "Тренинг"),
        ("other", "Иное"),
    ]

    LOCATION_TYPES = [
        ("school", "Школа (актовый зал, класс)"),
        ("street", "Улица / Пешеходный переход"),
        ("autotown", "Автогородок"),
        ("online", "Онлайн"),
        ("other", "Иное место"),
    ]

    title = models.CharField("Название", max_length=200)
    description = models.TextField("Описание", blank=True, null=True)
    date = models.DateField("Дата проведения")
    time = models.TimeField("Время начала", blank=True, null=True)
    status = models.CharField(
        "Статус", max_length=20, choices=STATUS_CHOICES, default="planned"
    )
    event_type = models.CharField(
        "Тип мероприятия", max_length=30, choices=EVENT_TYPES, default="lecture"
    )
    location_type = models.CharField(
        "Тип места", max_length=20, choices=LOCATION_TYPES, default="school"
    )
    
    tags = models.CharField("Теги", max_length=500, blank=True, null=True, help_text="Введите теги через запятую")
    responsible_person = models.CharField("Ответственное лицо", max_length=200, blank=True, null=True)

    location_address = models.CharField(
        "Место проведения", max_length=300, blank=True, null=True
    )
    district = models.CharField('Район', max_length=100, blank=True, null=True)
    latitude = models.FloatField("Широта", blank=True, null=True)
    longitude = models.FloatField("Долгота", blank=True, null=True)

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, verbose_name="Организация-проводитель"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="Создал"
    )

    report_link = models.URLField("Ссылка на отчет", blank=True, null=True)
    gibdd_approved = models.BooleanField("Подтверждено ГИБДД", default=False)


    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.date}"

    class Meta:
        verbose_name = "Мероприятие"
        verbose_name_plural = "Мероприятия"
        ordering = ["-date"]


class Accident(models.Model):
    SEVERITY_CHOICES = [
        ("light", "Легкое"),
        ("medium", "Среднее"),
        ("heavy", "Тяжелое"),
        ("fatal", "Смертельное"),
    ]

    title = models.CharField("Название", max_length=200)
    
    description = models.TextField("Описание")
    date = models.DateTimeField("Дата и время ДТП")
    location_address = models.CharField("Место", max_length=300, blank=True, null=True)
    district = models.CharField('Район', max_length=100, blank=True, null=True)
    latitude = models.FloatField("Широта", blank=True, null=True)
    longitude = models.FloatField("Долгота", blank=True, null=True)
    severity = models.CharField(
        "Тяжесть", max_length=20, choices=SEVERITY_CHOICES, default="light"
    )
    tags = models.TextField("Теги", blank=True, null=True)
    cluster_hash = models.CharField('Хеш кластера', max_length=32, blank=True, null=True, db_index=True)

    related_organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Связанная организация",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.date.strftime('%d.%m.%Y')}"

    class Meta:
        verbose_name = "ДТП"
        verbose_name_plural = "ДТП"
        ordering = ["-date"]

    def get_severity_display(self):
        return dict(self.SEVERITY_CHOICES).get(self.severity, self.severity)




class Plan(models.Model):
    MONTH_CHOICES = [
        (1, "Январь"),
        (2, "Февраль"),
        (3, "Март"),
        (4, "Апрель"),
        (5, "Май"),
        (6, "Июнь"),
        (7, "Июль"),
        (8, "Август"),
        (9, "Сентябрь"),
        (10, "Октябрь"),
        (11, "Ноябрь"),
        (12, "Декабрь"),
    ]

    year = models.IntegerField("Год")
    month = models.IntegerField("Месяц", choices=MONTH_CHOICES)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, verbose_name="Организация"
    )
    target_count = models.IntegerField("Плановое количество мероприятий", default=1)
    completed_count = models.IntegerField("Выполнено мероприятий", default=0)
    notes = models.TextField("Примечания", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "План мероприятий"
        verbose_name_plural = "Планы мероприятий"
        unique_together = ["year", "month", "organization"]

class ReportFile(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='report_files')
    file = models.FileField('Файл', upload_to='reports/%Y/%m/%d/')
    filename = models.CharField('Имя файла', max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename

    class Meta:
        verbose_name = 'Файл отчета'
        verbose_name_plural = 'Файлы отчетов'

class Invitation(models.Model):
    email = models.EmailField("Email сотрудника")
    token = models.CharField("Токен", max_length=64, unique=True)
    used = models.BooleanField("Использовано", default=False)
    max_uses = models.IntegerField("Максимум использований", default=1)
    used_count = models.IntegerField("Использовано раз", default=0)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    
    def is_valid(self):
        return self.used_count < self.max_uses
    
    def __str__(self):
        return f"Токен: {self.token[:8]}... (использовано {self.used_count}/{self.max_uses})"