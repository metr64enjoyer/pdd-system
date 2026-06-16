import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from django.conf import settings
from .models import Accident, Organization

ML_MODELS_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
os.makedirs(ML_MODELS_DIR, exist_ok=True)

MODEL_PATH = os.path.join(ML_MODELS_DIR, 'category_classifier.pkl')
VECTORIZER_PATH = os.path.join(ML_MODELS_DIR, 'tfidf_vectorizer.pkl')
LABEL_ENCODER_PATH = os.path.join(ML_MODELS_DIR, 'label_encoder.pkl')
RECOMMENDER_PATH = os.path.join(ML_MODELS_DIR, 'event_recommender.pkl')
REC_ENCODER_PATH = os.path.join(ML_MODELS_DIR, 'rec_label_encoder.pkl')
DANGER_PATH = os.path.join(ML_MODELS_DIR, 'danger_classifier.pkl')
DANGER_ENCODER_PATH = os.path.join(ML_MODELS_DIR, 'danger_label_encoder.pkl')


def get_prevention_category(text):
    """Извлекает категорию ДТП напрямую из датасета"""
    import re
    cat_match = re.search(r'Категория:\s*([^\.]+)', str(text))
    if cat_match:
        return cat_match.group(1).strip()
    return 'Общие ДТП'


def prepare_training_data():
    """Подготавливает данные из базы ДТП для обучения"""
    accidents = Accident.objects.all()
    
    data = []
    for a in accidents:
        data.append({
            'title': a.title or '',
            'description': a.description or '',
            'severity': a.severity or 'light',
            'district': a.district or '',
            'address': a.location_address or '',
        })
    
    df = pd.DataFrame(data)
    
    df['text_features'] = (
        df['title'].fillna('') + ' ' + 
        df['description'].fillna('') + ' ' + 
        df['address'].fillna('') + ' ' + 
        df['district'].fillna('')
    )
    
    df['prevention_category'] = df['text_features'].apply(get_prevention_category)
    
    print("Распределение категорий:")
    print(df['prevention_category'].value_counts())
    
    vectorizer = TfidfVectorizer(max_features=1000)
    X_text = vectorizer.fit_transform(df['text_features'])
    
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(df['prevention_category'])
    
    print(f"Размер признаков: {X_text.shape}")
    print(f"Категории: {list(label_encoder.classes_)}")
    
    return X_text, y, vectorizer, label_encoder


def generate_recommendation_training_data():
    """Генерирует синтетические данные для обучения модели рекомендаций"""
    np.random.seed(42)
    samples = []
    
    for _ in range(5000):
        total = np.random.randint(0, 30)
        light = np.random.randint(0, total + 1)
        heavy = np.random.randint(0, total - light + 1)
        fatal = total - light - heavy
        
        pedestrians = np.random.randint(0, total + 1)
        cyclists = np.random.randint(0, total + 1)
        children = np.random.randint(0, total + 1)
        speed = np.random.randint(0, total + 1)
        
        # Правила разметки (учитель)
        if fatal >= 2 or heavy >= 5:
            rec = 'action'
        elif fatal >= 1:
            rec = 'briefing'
        elif children >= 3:
            rec = 'parent_meeting'
        elif pedestrians >= 5:
            rec = 'practical'
        elif cyclists >= 3:
            rec = 'practical'
        elif speed >= 3:
            rec = 'action'
        elif heavy >= 3:
            rec = 'briefing'
        elif total >= 10:
            rec = 'lecture'
        else:
            rec = 'lecture'
        
        samples.append({
            'total': total, 'light': light, 'heavy': heavy, 'fatal': fatal,
            'pedestrians': pedestrians, 'cyclists': cyclists,
            'children': children, 'speed': speed,
            'recommendation': rec
        })
    
    return pd.DataFrame(samples)


def generate_danger_training_data():
    """Генерирует синтетические данные для обучения модели уровня опасности"""
    np.random.seed(42)
    samples = []
    
    for _ in range(5000):
        total = np.random.randint(0, 30)
        heavy = np.random.randint(0, total + 1)
        fatal = np.random.randint(0, min(3, total - heavy) + 1)
        light = total - heavy - fatal
        
        # Правила разметки (учитель)
        if fatal >= 2 or heavy >= 5 or total >= 15:
            danger = 'high'
        elif fatal >= 1 or heavy >= 3 or total >= 8:
            danger = 'medium'
        else:
            danger = 'low'
        
        samples.append({
            'total': total, 'light': light, 'heavy': heavy, 'fatal': fatal,
            'danger': danger
        })
    
    return pd.DataFrame(samples)


def train_models():
    """Обучает все три модели и сохраняет их"""
    
    # 1. Классификатор категорий ДТП
    print("=" * 60)
    print("1/3: ОБУЧЕНИЕ КЛАССИФИКАТОРА КАТЕГОРИЙ ДТП")
    print("=" * 60)
    
    X, y, vectorizer, label_encoder = prepare_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"Обучающая: {X_train.shape[0]} | Тестовая: {X_test.shape[0]}")
    
    cat_model = RandomForestClassifier(n_estimators=100, max_depth=20, random_state=42, n_jobs=-1)
    cat_model.fit(X_train, y_train)
    
    y_pred = cat_model.predict(X_test)
    cat_accuracy = accuracy_score(y_test, y_pred)
    print(f"Точность категорий: {cat_accuracy:.2%}")
    
    joblib.dump(cat_model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(label_encoder, LABEL_ENCODER_PATH)
    print("Сохранено: category_classifier.pkl, tfidf_vectorizer.pkl, label_encoder.pkl")
    
    # 2. Рекомендательная модель (ML, не if-else!)
    print("\n" + "=" * 60)
    print("2/3: ОБУЧЕНИЕ РЕКОМЕНДАТЕЛЬНОЙ МОДЕЛИ (Random Forest)")
    print("=" * 60)
    
    df_rec = generate_recommendation_training_data()
    feature_cols = ['total', 'light', 'heavy', 'fatal', 'pedestrians', 'cyclists', 'children', 'speed']
    X_rec = df_rec[feature_cols]
    y_rec = df_rec['recommendation']
    
    rec_encoder = LabelEncoder()
    y_rec_enc = rec_encoder.fit_transform(y_rec)
    
    Xr_train, Xr_test, yr_train, yr_test = train_test_split(X_rec, y_rec_enc, test_size=0.2, random_state=42)
    
    rec_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rec_model.fit(Xr_train, yr_train)
    
    yr_pred = rec_model.predict(Xr_test)
    rec_accuracy = accuracy_score(yr_test, yr_pred)
    print(f"Точность рекомендаций: {rec_accuracy:.2%}")
    
    joblib.dump(rec_model, RECOMMENDER_PATH)
    joblib.dump(rec_encoder, REC_ENCODER_PATH)
    print("Сохранено: event_recommender.pkl, rec_label_encoder.pkl")
    
    # 3. Классификатор уровня опасности (ML, не if-else!)
    print("\n" + "=" * 60)
    print("3/3: ОБУЧЕНИЕ КЛАССИФИКАТОРА ОПАСНОСТИ (Random Forest)")
    print("=" * 60)
    
    df_danger = generate_danger_training_data()
    X_danger = df_danger[['total', 'light', 'heavy', 'fatal']]
    y_danger = df_danger['danger']
    
    danger_encoder = LabelEncoder()
    y_danger_enc = danger_encoder.fit_transform(y_danger)
    
    Xd_train, Xd_test, yd_train, yd_test = train_test_split(X_danger, y_danger_enc, test_size=0.2, random_state=42)
    
    danger_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    danger_model.fit(Xd_train, yd_train)
    
    yd_pred = danger_model.predict(Xd_test)
    danger_accuracy = accuracy_score(yd_test, yd_pred)
    print(f"Точность опасности: {danger_accuracy:.2%}")
    
    joblib.dump(danger_model, DANGER_PATH)
    joblib.dump(danger_encoder, DANGER_ENCODER_PATH)
    print("Сохранено: danger_classifier.pkl, danger_label_encoder.pkl")
    
    print("\n" + "=" * 60)
    print("ВСЕ МОДЕЛИ ОБУЧЕНЫ И СОХРАНЕНЫ")
    print(f"  {MODEL_PATH}")
    print(f"  {RECOMMENDER_PATH}")
    print(f"  {DANGER_PATH}")
    print("=" * 60)
    
    return cat_accuracy, rec_accuracy, danger_accuracy


def predict_category(text):
    """Предсказывает категорию ДТП через ML"""
    if not os.path.exists(MODEL_PATH):
        return 'Общие ДТП', 0.0
    
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    encoder = joblib.load(LABEL_ENCODER_PATH)
    
    X = vectorizer.transform([text])
    pred = model.predict(X)[0]
    category = encoder.inverse_transform([pred])[0]
    confidence = max(model.predict_proba(X)[0])
    
    return category, confidence


def predict_recommendation(stats):
    """Предсказывает тип мероприятия через ML (100 деревьев голосуют)"""
    if not os.path.exists(RECOMMENDER_PATH):
        return 'lecture', 1.0
    
    model = joblib.load(RECOMMENDER_PATH)
    encoder = joblib.load(REC_ENCODER_PATH)
    
    features = np.array([[
        stats.get('total', 0), stats.get('light', 0),
        stats.get('heavy', 0), stats.get('fatal', 0),
        stats.get('pedestrians', 0), stats.get('cyclists', 0),
        stats.get('children', 0), stats.get('speed', 0),
    ]])
    
    # 100 деревьев голосуют → выбирается большинство
    pred = model.predict(features)[0]
    event_type = encoder.inverse_transform([pred])[0]
    confidence = max(model.predict_proba(features)[0])
    
    return event_type, confidence


def predict_danger(stats):
    """Предсказывает уровень опасности через ML (100 деревьев голосуют)"""
    if not os.path.exists(DANGER_PATH):
        return 'low', 1.0
    
    model = joblib.load(DANGER_PATH)
    encoder = joblib.load(DANGER_ENCODER_PATH)
    
    features = np.array([[
        stats.get('total', 0), stats.get('light', 0),
        stats.get('heavy', 0), stats.get('fatal', 0),
    ]])
    
    # 100 деревьев голосуют → выбирается большинство
    pred = model.predict(features)[0]
    danger = encoder.inverse_transform([pred])[0]
    confidence = max(model.predict_proba(features)[0])
    
    return danger, confidence


def get_category_name(category):
    return str(category)


def get_event_recommendation(categories_count, nearby_accidents):
    if not categories_count or not nearby_accidents:
        return 'Лекция / Беседа', 'Недостаточно данных для рекомендации'
    
    top_category = max(categories_count, key=categories_count.get)
    total = sum(categories_count.values())
    
    # Собираем статистику по условиям из всех ДТП рядом
    conditions = {'Освещение': {}, 'Погода': {}, 'Нарушения': {}}
    for item in nearby_accidents:
        desc = item['accident'].description or ''
        import re
        for key, pattern in [('Освещение', r'Освещение:\s*([^\.]+)'), 
                              ('Погода', r'Погода:\s*([^\.]+)'),
                              ('Нарушения', r'Нарушения:\s*([^\.]+)')]:
            match = re.search(pattern, desc)
            if match:
                val = match.group(1).strip()
                conditions[key][val] = conditions[key].get(val, 0) + 1
    
    # Находим частые условия
    dark = sum(v for k, v in conditions['Освещение'].items() if 'темное' in k.lower() or 'тёмное' in k.lower() or 'сумерки' in k.lower())
    bad_weather = sum(v for k, v in conditions['Погода'].items() if 'снег' in k.lower() or 'дожд' in k.lower() or 'туман' in k.lower())
    speed_violations = sum(v for k, v in conditions['Нарушения'].items() if 'скорост' in k.lower())
    
    # Типы мероприятий под категорию
    types = {
        'Наезд на пешехода': 'Практическое занятие',
        'Столкновение': 'Лекция / Беседа',
        'Съезд с дороги': 'Инструктаж',
        'Наезд на препятствие': 'Лекция / Беседа',
        'Опрокидывание': 'Инструктаж',
        'Наезд на велосипедиста': 'Акция / Рейд',
        'Падение пассажира': 'Инструктаж',
        'Наезд на стоящее ТС': 'Лекция / Беседа',
        'Наезд на животное': 'Инструктаж',
    }
    
    event_type = types.get(top_category, 'Лекция / Беседа')
    
    # Генерируем обоснование
    parts = [f'Рекомендуется {event_type.lower()} по профилактике ДТП категории «{top_category}»']
    
    if dark > total * 0.3:
        parts.append('С акцентом на безопасность в тёмное время суток и использование световозвращающих элементов')
    
    if bad_weather > total * 0.2:
        parts.append('С учётом неблагоприятных погодных условий')
    
    if speed_violations > total * 0.2:
        parts.append('С разбором нарушений скоростного режима')
    
    reason = '. '.join(parts) + f' '
    
    return event_type, reason


def get_danger_name(danger):
    return {'high': 'Высокий', 'medium': 'Средний', 'low': 'Низкий'}.get(danger, danger)


def calculate_distance(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, asin
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))

def get_address_from_coords(lat, lng):
    """Получает адрес по координатам через Яндекс.Геокодер"""
    if not lat or not lng:
        return ''
    
    import requests
    from django.conf import settings
    
    try:
        url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            'apikey': settings.YANDEX_API_KEY,
            'geocode': f"{lng},{lat}",
            'format': 'json',
            'results': 1
        }
        response = requests.get(url, params=params, timeout=3)
        data = response.json()
        
        geo_objects = data.get('response', {}).get('GeoObjectCollection', {}).get('featureMember', [])
        if geo_objects:
            return geo_objects[0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['text']
    except:
        pass
    
    return f"{lat:.5f}, {lng:.5f}"


def analyze_school(school_id, year=None, radius=500):
    """Полный анализ ДТП вокруг школы с ML-предсказаниями"""
    try:
        school = Organization.objects.get(id=school_id)
    except Organization.DoesNotExist:
        return {'error': 'Школа не найдена'}
    
    if not school.latitude or not school.longitude:
        return {'error': 'Нет координат школы', 'school_name': school.name}
    
    accidents = Accident.objects.filter(
        latitude__isnull=False, longitude__isnull=False
    ).exclude(latitude=0, longitude=0)
    
    if year:
        accidents = accidents.filter(date__year=year)
    
    nearby = []
    for a in accidents:
        dist = calculate_distance(school.latitude, school.longitude, a.latitude, a.longitude)
        if dist <= radius:
            nearby.append({'accident': a, 'distance': round(dist, 1)})
    
    total = len(nearby)
    categories_count = {}
    severity_count = {'light': 0, 'medium': 0, 'heavy': 0, 'fatal': 0}
    model_exists = os.path.exists(MODEL_PATH)
    
    for item in nearby:
        a = item['accident']
        text = f"{a.title} {a.description or ''} {a.location_address or ''} {a.district or ''}"
        cat, _ = predict_category(text) if model_exists else ('Общие ДТП', 0)
        categories_count[cat] = categories_count.get(cat, 0) + 1
        severity_count[a.severity] = severity_count.get(a.severity, 0) + 1
    
    # Статистика для ML-моделей
    stats = {
        'total': total,
        'light': severity_count['light'],
        'heavy': severity_count['heavy'],
        'fatal': severity_count['fatal'],
        'pedestrians': categories_count.get('Пешеходы', 0),
        'cyclists': categories_count.get('Велосипедисты', 0),
        'children': categories_count.get('Дети', 0),
        'speed': categories_count.get('Нарушения скорости', 0),
    }
    
    # ML-предсказания (100 деревьев голосуют)
    event_type, reason = get_event_recommendation(categories_count, nearby)
    danger, danger_conf = predict_danger(stats)
    
    categories_list = []
    for cat, cnt in sorted(categories_count.items(), key=lambda x: x[1], reverse=True):
        categories_list.append({
            'category': cat, 'name': get_category_name(cat),
            'count': cnt,
            'percent': round(cnt / total * 100, 1) if total > 0 else 0,
        })
    
    accidents_sorted = sorted(nearby, key=lambda x: x['distance'])[:20]
    accidents_list = [{
        'id': item['accident'].id,
        'title': item['accident'].title,
        'date': item['accident'].date.strftime('%d.%m.%Y'),
        'severity': item['accident'].get_severity_display(),
        'address': item['accident'].location_address or get_address_from_coords(item['accident'].latitude, item['accident'].longitude),
        'distance': item['distance'],
    } for item in accidents_sorted]
    
    return {
        'school_id': school.id,
        'school_name': school.name,
        'school_address': school.address or '',
        'total_accidents': total,
        'severity_count': severity_count,
        'categories': categories_list,
        'recommendation': {
            'type': event_type,
            'name': event_type,
            'reason': reason,
        },
        'danger_level': danger,
        'danger_level_name': get_danger_name(danger),
        'danger_confidence': round(danger_conf * 100, 1),
        'accidents_list': accidents_list,
        'model_trained': model_exists,
    }


def get_all_schools_summary(year=None):
    """Сводка по всем школам"""
    organizations = Organization.objects.filter(
        latitude__isnull=False, longitude__isnull=False
    ).exclude(latitude=0, longitude=0)
    
    summary = []
    for org in organizations:
        analysis = analyze_school(org.id, year=year)
        if 'error' not in analysis:
            summary.append({
                'school_id': org.id,
                'school_name': org.name,
                'total_accidents': analysis['total_accidents'],
                'danger_level': analysis['danger_level_name'],
                'recommendation': analysis['recommendation']['name'],
            })
    
    summary.sort(key=lambda x: x['total_accidents'], reverse=True)
    return summary