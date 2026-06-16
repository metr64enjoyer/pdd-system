from django.contrib import admin
from .models import Organization, UserProfile, Event, Accident, Plan, ReportFile, Invitation
import uuid


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'inn', 'phone', 'is_active')
    search_fields = ('name', 'inn')
    list_filter = ('is_active',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'organization', 'phone', 'yuid_name')
    search_fields = ('user__username', 'user__email')
    list_filter = ('user_type',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'date', 'status', 'event_type')
    search_fields = ('title', 'organization__name')
    list_filter = ('status', 'date', 'event_type')
    date_hierarchy = 'date'


@admin.register(Accident)
class AccidentAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'severity', 'location_address')
    search_fields = ('title', 'description')
    list_filter = ('severity', 'date')
    date_hierarchy = 'date'


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('organization', 'year', 'month', 'target_count', 'completed_count')
    list_filter = ('year', 'month')


@admin.register(ReportFile)
class ReportFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'event', 'uploaded_at')
    search_fields = ('filename', 'event__title')
    list_filter = ('uploaded_at',)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'token', 'used', 'created_at')
    list_filter = ('used',)
    search_fields = ('email',)
    readonly_fields = ('token', 'created_at')
    actions = ['create_invitation_link']
    
    def save_model(self, request, obj, form, change):
        if not obj.token:
            obj.token = str(uuid.uuid4()).replace('-', '')[:32]
        super().save_model(request, obj, form, change)
    
    @admin.action(description='Создать ссылку-приглашение')
    def create_invitation_link(self, request, queryset):
        from django.urls import reverse
        for invite in queryset:
            if not invite.token:
                invite.token = str(uuid.uuid4()).replace('-', '')[:32]
                invite.save()
            link = request.build_absolute_uri(reverse('register_by_invite', args=[invite.token]))
            self.message_user(request, f'Ссылка для {invite.email}: {link}')