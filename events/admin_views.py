import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Organization, UserProfile, Event, Accident
from .models import Invitation
import uuid
from django.db.models import Q

# ==================== ОСНОВНЫЕ СТРАНИЦЫ ====================

@login_required
@staff_member_required
def admin_dashboard(request):
    """Главная страница админ-панели"""
    from datetime import datetime, timedelta
    from django.db.models import Count, Q
    
    # Основные счётчики
    schools_count = Organization.objects.count()
    users_count = UserProfile.objects.count()
    events_count = Event.objects.count()
    accidents_count = Accident.objects.count()
    
    # За последние 30 дней
    last_month = datetime.now() - timedelta(days=30)
    new_events = Event.objects.filter(created_at__gte=last_month).count()
    new_accidents = Accident.objects.filter(created_at__gte=last_month).count()
    new_users = UserProfile.objects.filter(created_at__gte=last_month).count()
    
    # Мероприятия по статусам
    events_planned = Event.objects.filter(status='planned').count()
    events_conducted = Event.objects.filter(status='conducted').count()
    events_approved = Event.objects.filter(status='approved').count()
    
    # ДТП по тяжести
    dtp_light = Accident.objects.filter(severity='light').count()
    dtp_heavy = Accident.objects.filter(severity='heavy').count()
    dtp_fatal = Accident.objects.filter(severity='fatal').count()
    
    # Пользователи по типам
    org_users = UserProfile.objects.filter(user_type='organization').count()
    propaganda_users = UserProfile.objects.filter(user_type='propaganda').count()
    
    # Последние 5 мероприятий
    recent_events = Event.objects.select_related('organization').order_by('-created_at')[:5]
    
    # Школы с наибольшим числом мероприятий
    top_schools = Organization.objects.annotate(
        event_count=Count('event')
    ).order_by('-event_count')[:5]
    
    context = {
        'schools_count': schools_count,
        'users_count': users_count,
        'events_count': events_count,
        'accidents_count': accidents_count,
        'new_events': new_events,
        'new_accidents': new_accidents,
        'new_users': new_users,
        'events_planned': events_planned,
        'events_conducted': events_conducted,
        'events_approved': events_approved,
        'dtp_light': dtp_light,
        'dtp_heavy': dtp_heavy,
        'dtp_fatal': dtp_fatal,
        'org_users': org_users,
        'propaganda_users': propaganda_users,
        'recent_events': recent_events,
        'top_schools': top_schools,
    }
    return render(request, 'admin_dashboard.html', context)


@login_required
@staff_member_required
def admin_schools(request):
    """Управление школами с сортировкой, поиском и массовым удалением"""
    if not request.user.is_superuser:
        return redirect('home')
    
    # Обработка массового удаления
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if data.get('action') == 'delete_selected':
                ids = data.get('ids', [])
                Organization.objects.filter(id__in=ids).delete()
                return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False})
    
    schools_all = Organization.objects.all()
    
    # Поиск
    search = request.GET.get('search', '')
    if search:
        schools_all = schools_all.filter(name__icontains=search)
    
    # Сортировка
    sort = request.GET.get('sort', 'name')
    allowed_sorts = ['id', '-id', 'name', '-name', 'inn', '-inn']
    if sort in allowed_sorts:
        schools_all = schools_all.order_by(sort)
    else:
        schools_all = schools_all.order_by('name')
    
    paginator = Paginator(schools_all, 20)
    page_number = request.GET.get('page', 1)
    schools = paginator.get_page(page_number)
    
    return render(request, 'admin_schools.html', {
        'schools': schools,
        'page_obj': schools,
        'search': search,
    })


@login_required
@staff_member_required
def admin_users(request):
    """Управление пользователями с сортировкой, поиском и фильтрацией"""
    if not request.user.is_superuser:
        return redirect('home')
    
    # Обработка массового удаления
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if data.get('action') == 'delete_selected':
                ids = data.get('ids', [])
                from django.contrib.auth.models import User
                User.objects.filter(id__in=ids).delete()
                return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False})
    
    profiles_all = UserProfile.objects.select_related('user', 'organization').all()
    
    # Поиск по ФИО
    search = request.GET.get('search', '')
    if search:
        from django.db.models import Q
        profiles_all = profiles_all.filter(
            Q(user__last_name__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(patronymic__icontains=search) |
            Q(user__username__icontains=search)
        )
    
    # Фильтрация по типу
    user_type_filter = request.GET.get('user_type', '')
    if user_type_filter:
        profiles_all = profiles_all.filter(user_type=user_type_filter)
    
    # Сортировка по ID
    sort = request.GET.get('sort', '')
    if sort == 'id':
        profiles_all = profiles_all.order_by('user__id')
    elif sort == '-id':
        profiles_all = profiles_all.order_by('-user__id')
    
    paginator = Paginator(profiles_all, 20)
    page_number = request.GET.get('page', 1)
    profiles = paginator.get_page(page_number)
    
    schools = Organization.objects.all().order_by('name')
    return render(request, 'admin_users.html', {
        'profiles': profiles,
        'schools': schools,
        'page_obj': profiles,
        'search': search,
        'user_type_filter': user_type_filter,
    })

@login_required
@staff_member_required
def admin_events(request):
    """Управление мероприятиями с поиском, фильтрацией, сортировкой и массовым удалением"""
    if not request.user.is_superuser:
        return redirect('home')
    
    # Обработка массового удаления
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if data.get('action') == 'delete_selected':
                ids = data.get('ids', [])
                Event.objects.filter(id__in=ids).delete()
                return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False})
    
    events_all = Event.objects.select_related('organization').all()
    
    # Поиск по названию или адресу
    search = request.GET.get('search', '')
    if search:
        events_all = events_all.filter(
            Q(title__icontains=search) | Q(location_address__icontains=search)
        )
    
    # Фильтр по статусу
    status_filter = request.GET.get('status', '')
    if status_filter:
        events_all = events_all.filter(status=status_filter)
    
    # Фильтр по организации
    organization_filter = request.GET.get('organization', '')
    if organization_filter:
        events_all = events_all.filter(organization_id=organization_filter)
    
    # Сортировка
    sort = request.GET.get('sort', '-date')
    if sort in ['id', '-id', 'date', '-date']:
        events_all = events_all.order_by(sort)
    else:
        events_all = events_all.order_by('-date')
    
    # Пагинация
    paginator = Paginator(events_all, 20)
    page_number = request.GET.get('page', 1)
    events = paginator.get_page(page_number)
    
    # Все организации для фильтра
    all_organizations = Organization.objects.all().order_by('name')
    
    return render(request, 'admin_events.html', {
        'events': events,
        'page_obj': events,
        'search': search,
        'status_filter': status_filter,
        'organization_filter': organization_filter,
        'all_organizations': all_organizations,
    })


@login_required
@staff_member_required
def admin_accidents(request):
    if not request.user.is_superuser:
        return redirect('home')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if data.get('action') == 'delete_selected':
                ids = data.get('ids', [])
                Accident.objects.filter(id__in=ids).delete()
                return JsonResponse({'success': True})
            if data.get('action') == 'delete_batch':
                batch_size = data.get('batch_size', 1000)
                ids = list(Accident.objects.values_list('id', flat=True)[:batch_size])
                count = len(ids)
                Accident.objects.filter(id__in=ids).delete()
                remaining = Accident.objects.count()
                return JsonResponse({'success': True, 'deleted': count, 'remaining': remaining})
        except:
            return JsonResponse({'success': False})
    
    accidents_all = Accident.objects.all().order_by('-date')
    
    # Поиск по названию И адресу одновременно
    search = request.GET.get('search', '')
    if search:
        accidents_all = accidents_all.filter(
            Q(title__icontains=search) | Q(location_address__icontains=search)
        )
    
    # Фильтр по тяжести
    severity_filter = request.GET.get('severity', '')
    if severity_filter:
        accidents_all = accidents_all.filter(severity=severity_filter)
    
    # Фильтр по дате "с"
    date_from = request.GET.get('date_from', '')
    if date_from:
        accidents_all = accidents_all.filter(date__gte=date_from)
    
    # Фильтр по дате "по"
    date_to = request.GET.get('date_to', '')
    if date_to:
        accidents_all = accidents_all.filter(date__lte=date_to)
    
    # Пагинация
    paginator = Paginator(accidents_all, 20)
    page_number = request.GET.get('page', 1)
    accidents = paginator.get_page(page_number)
    
    return render(request, 'admin_accidents.html', {
        'accidents': accidents,
        'page_obj': accidents,
        'search': search,
        'severity_filter': severity_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


# ==================== ШКОЛЫ (CRUD) ====================

def admin_add_school(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        inn = request.POST.get('inn')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        
        if name and inn:
            Organization.objects.create(
                name=name,
                inn=inn,
                address=address,
                phone=phone,
                email=email,
                is_active=True
            )
            messages.success(request, 'Школа добавлена')
        else:
            messages.error(request, 'Название и ИНН обязательны')
    
    return redirect('admin_schools')


def admin_edit_school(request):
    if request.method == 'POST':
        school_id = request.POST.get('school_id')
        school = get_object_or_404(Organization, id=school_id)
        school.name = request.POST.get('name')
        school.inn = request.POST.get('inn')
        school.address = request.POST.get('address')
        school.phone = request.POST.get('phone')
        school.email = request.POST.get('email')
        school.is_active = request.POST.get('is_active') == 'on'
        school.save()
        messages.success(request, 'Школа обновлена')
    return redirect('admin_schools')


def admin_delete_school(request):
    if request.method == 'POST':
        school_id = request.POST.get('school_id')
        school = get_object_or_404(Organization, id=school_id)
        school.delete()
        messages.success(request, 'Школа удалена')
    return redirect('admin_schools')


# ==================== ПОЛЬЗОВАТЕЛИ (CRUD) ====================

def admin_add_user(request):
    if request.method == 'POST':
        from django.contrib.auth.models import User
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        last_name = request.POST.get('last_name', '')
        first_name = request.POST.get('first_name', '')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким логином уже существует')
            return redirect('admin_users')
        
        user = User.objects.create_user(username=username, password=password, email=email)
        user.last_name = last_name
        user.first_name = first_name
        user.save()
        
        profile, created = UserProfile.objects.get_or_create(user=user)
        user_type = request.POST.get('user_type', 'organization')
        profile.user_type = user_type

        # Если выбран тип admin, делаем пользователя суперпользователем
        if user_type == 'admin':
            user.is_staff = True
            user.is_superuser = True
            user.save()
        profile.patronymic = request.POST.get('patronymic', '')
        profile.yuid_name = request.POST.get('yuid_name', '')
        profile.phone = request.POST.get('phone', '')
        org_id = request.POST.get('organization_id')
        if org_id:
            profile.organization_id = org_id
        profile.save()
        
        messages.success(request, 'Пользователь добавлен')
    return redirect('admin_users')


def admin_edit_user(request):
    if request.method == 'POST':
        from django.contrib.auth.models import User
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.last_name = request.POST.get('last_name', '')
        user.first_name = request.POST.get('first_name', '')
        
        password = request.POST.get('password')
        if password:
            user.set_password(password)
        user.save()
        
        profile = user.profile
        user_type = request.POST.get('user_type', 'organization')
        profile.user_type = user_type

        if user_type == 'admin':
            user.is_staff = True
            user.is_superuser = True
            user.save()
        else:
            user.is_staff = False
            user.is_superuser = False
            user.save()
        profile.patronymic = request.POST.get('patronymic', '')
        profile.yuid_name = request.POST.get('yuid_name', '')
        profile.phone = request.POST.get('phone', '')
        org_id = request.POST.get('organization_id')
        profile.organization_id = org_id if org_id else None
        profile.save()
        
        messages.success(request, 'Пользователь обновлён')
    return redirect('admin_users')


def admin_delete_user(request):
    if request.method == 'POST':
        from django.contrib.auth.models import User
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        user.delete()
        # Если у пользователя была организация — удаляем и её
    if hasattr(user, 'profile') and user.profile.organization:
        org = user.profile.organization
        # Проверяем, не привязана ли организация к другим пользователям
        other_users = UserProfile.objects.filter(organization=org).exclude(user=user).count()
        if other_users == 0:
            org.delete()
        messages.success(request, 'Пользователь удалён')
    return redirect('admin_users')



# ==================== МЕРОПРИЯТИЯ (CRUD) ====================

def admin_edit_event(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        event.title = request.POST.get('title')
        event.date = request.POST.get('date')
        event.time = request.POST.get('time') or None
        event.status = request.POST.get('status')
        event.event_type = request.POST.get('event_type')
        event.district = request.POST.get('district')
        event.location_address = request.POST.get('location_address')
        event.responsible_person = request.POST.get('responsible_person')
        event.tags = request.POST.get('tags')
        event.description = request.POST.get('description')
        event.save()
        messages.success(request, 'Мероприятие обновлено')
    return redirect('admin_events')


def admin_delete_event(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        event.delete()
        messages.success(request, 'Мероприятие удалено')
    return redirect('admin_events')


# ==================== ДТП (CRUD) ====================

def admin_edit_accident(request):
    if request.method == 'POST':
        accident_id = request.POST.get('accident_id')
        accident = get_object_or_404(Accident, id=accident_id)
        accident.title = request.POST.get('title')
        accident.date = request.POST.get('date')
        accident.location_address = request.POST.get('location_address')
        accident.district = request.POST.get('district')
        accident.severity = request.POST.get('severity')
        accident.description = request.POST.get('description')
        accident.save()
        messages.success(request, 'ДТП обновлено')
    return redirect('admin_accidents')


def admin_delete_accident(request):
    if request.method == 'POST':
        accident_id = request.POST.get('accident_id')
        accident = get_object_or_404(Accident, id=accident_id)
        accident.delete()
        messages.success(request, 'ДТП удалено')
    return redirect('admin_accidents')


# ==================== ПРИГЛАШЕНИЯ ====================

def admin_invitations(request):
    if not request.user.is_superuser:
        return redirect('home')
    
    # Обработка массового удаления (JSON запрос)
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            if data.get('action') == 'delete_selected':
                ids = data.get('ids', [])
                Invitation.objects.filter(id__in=ids).delete()
                return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False})
    
    # Обработка создания токена (обычная форма)
    generated_link = None
    
    if request.method == 'POST' and 'max_uses' in request.POST:
        max_uses = int(request.POST.get('max_uses', 1))
        token = str(uuid.uuid4()).replace('-', '')[:32]
        Invitation.objects.create(
            email=f'multi_use_{token[:8]}',
            token=token,
            used=False,
            max_uses=max_uses,
            used_count=0
        )
        generated_link = request.build_absolute_uri(f'/register/invite/{token}/')
        messages.success(request, f'Создан токен на {max_uses} использований')
    
    invitations_all = Invitation.objects.all().order_by('-created_at')
    paginator = Paginator(invitations_all, 20)
    page_number = request.GET.get('page', 1)
    invitations = paginator.get_page(page_number)
    
    return render(request, 'admin_invitations.html', {
        'invitations': invitations,
        'generated_link': generated_link,
        'page_obj': invitations
    })