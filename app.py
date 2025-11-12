import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, User, Event, Team, Achievement, UserAchievement, PollutedPlace
from PIL import Image

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'toloka-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///toloka.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://',
                                                                                          'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Будь ласка, увійдіть для доступу до цієї сторінки'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def optimize_image(image_path, max_size=(800, 800)):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(image_path, optimize=True, quality=85)
    except Exception as e:
        print(f"Error optimizing image: {e}")


def check_achievements(user):
    achievements_to_grant = []
    all_achievements = Achievement.query.all()

    for achievement in all_achievements:
        already_has = UserAchievement.query.filter_by(
            user_id=user.id, achievement_id=achievement.id
        ).first()

        if already_has:
            continue

        should_grant = False
        if achievement.condition_type == 'events_count' and user.events_count >= achievement.condition_value:
            should_grant = True
        elif achievement.condition_type == 'waste_collected' and user.total_waste >= achievement.condition_value:
            should_grant = True
        elif achievement.condition_type == 'area_cleaned' and user.total_area >= achievement.condition_value:
            should_grant = True

        if should_grant:
            ua = UserAchievement(user_id=user.id, achievement_id=achievement.id)
            db.session.add(ua)
            achievements_to_grant.append(achievement.name)

    if achievements_to_grant:
        db.session.commit()
    return achievements_to_grant


@app.route('/')
def index():
    upcoming_events = Event.query.filter(
        Event.date >= datetime.utcnow(),
        Event.status == 'planned'
    ).order_by(Event.date).limit(6).all()

    stats = {
        'total_events': Event.query.filter_by(status='completed').count(),
        'total_waste': db.session.query(db.func.sum(Event.waste_collected)).scalar() or 0,
        'total_area': db.session.query(db.func.sum(Event.area_cleaned)).scalar() or 0,
        'total_users': User.query.count()
    }

    return render_template('index.html', events=upcoming_events, stats=stats)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()

        if not username or not email or not password:
            flash('Заповніть всі обовʼязкові поля', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Користувач з таким іменем вже існує', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email вже зареєстрований', 'danger')
            return redirect(url_for('register'))

        user = User(username=username, email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Реєстрація успішна! Тепер увійдіть в систему.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Успішний вхід!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Невірне імʼя користувача або пароль', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ви вийшли з системи', 'info')
    return redirect(url_for('index'))


@app.route('/events/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        date_str = request.form.get('date')
        duration = request.form.get('duration', type=int)
        max_participants = request.form.get('max_participants', type=int)

        if not title or not location or not date_str:
            flash('Заповніть всі обовʼязкові поля', 'danger')
            return redirect(url_for('create_event'))

        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Невірний формат дати', 'danger')
            return redirect(url_for('create_event'))

        event = Event(
            title=title,
            description=description,
            location=location,
            latitude=latitude,
            longitude=longitude,
            date=event_date,
            duration=duration,
            max_participants=max_participants,
            creator_id=current_user.id
        )

        if 'image_before' in request.files:
            file = request.files['image_before']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                optimize_image(filepath)
                event.image_before = filename

        db.session.add(event)
        db.session.commit()

        flash('Подію успішно створено!', 'success')
        return redirect(url_for('event_detail', event_id=event.id))

    return render_template('event_create.html')


@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    is_participant = False
    if current_user.is_authenticated:
        is_participant = current_user in event.participants
    return render_template('event_detail.html', event=event, is_participant=is_participant)


@app.route('/events/<int:event_id>/join', methods=['POST'])
@login_required
def join_event(event_id):
    event = Event.query.get_or_404(event_id)

    if current_user in event.participants:
        flash('Ви вже зареєстровані на цю подію', 'info')
    elif event.max_participants and len(event.participants) >= event.max_participants:
        flash('Вибачте, місця закінчились', 'warning')
    else:
        event.participants.append(current_user)
        db.session.commit()
        flash('Ви успішно зареєструвались на подію!', 'success')

    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/events/<int:event_id>/leave', methods=['POST'])
@login_required
def leave_event(event_id):
    event = Event.query.get_or_404(event_id)

    if current_user in event.participants:
        event.participants.remove(current_user)
        db.session.commit()
        flash('Ви відмінили реєстрацію', 'info')

    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/events/<int:event_id>/complete', methods=['POST'])
@login_required
def complete_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.creator_id != current_user.id:
        flash('Тільки організатор може завершити подію', 'danger')
        return redirect(url_for('event_detail', event_id=event_id))

    waste = request.form.get('waste_collected', 0, type=float)
    area = request.form.get('area_cleaned', 0, type=float)

    event.waste_collected = waste
    event.area_cleaned = area
    event.status = 'completed'

    if 'image_after' in request.files:
        file = request.files['image_after']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            optimize_image(filepath)
            event.image_after = filename

    points_per_person = int(waste * 10 + area * 2)
    participant_count = len(event.participants)

    if participant_count > 0:
        for participant in event.participants:
            participant.points += points_per_person
            participant.events_count += 1
            participant.total_waste += waste / participant_count
            participant.total_area += area / participant_count

            new_achievements = check_achievements(participant)
            if new_achievements:
                flash(f'{participant.username} отримав досягнення: {", ".join(new_achievements)}', 'success')

    db.session.commit()
    flash('Подію завершено! Бали нараховано учасникам.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/calendar')
def calendar():
    events = Event.query.filter(
        Event.date >= datetime.utcnow(),
        Event.status == 'planned'
    ).order_by(Event.date).all()

    events_json = [{
        'id': e.id,
        'title': e.title,
        'start': e.date.isoformat(),
        'url': url_for('event_detail', event_id=e.id),
        'location': e.location
    } for e in events]

    return render_template('calendar.html', events_json=events_json)


@app.route('/map')
def map_view():
    polluted_places = PollutedPlace.query.filter_by(status='reported').all()
    events = Event.query.filter_by(status='planned').all()

    return render_template('map.html', polluted_places=polluted_places, events=events)


@app.route('/map/report', methods=['POST'])
@login_required
def report_pollution():
    data = request.get_json()

    place = PollutedPlace(
        title=data.get('title'),
        description=data.get('description'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        severity=data.get('severity', 'medium'),
        reporter_id=current_user.id
    )

    db.session.add(place)
    db.session.commit()

    return jsonify({'success': True, 'id': place.id})


@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    achievements = UserAchievement.query.filter_by(user_id=user.id).all()
    participated = user.participated_events[-10:]

    return render_template('profile.html', user=user, achievements=achievements, events=participated)


@app.route('/leaderboard')
def leaderboard():
    top_users = User.query.order_by(User.points.desc()).limit(50).all()
    return render_template('leaderboard.html', users=top_users)


@app.route('/teams')
def teams():
    all_teams = Team.query.order_by(Team.points.desc()).all()
    return render_template('teams.html', teams=all_teams)


@app.route('/teams/create', methods=['POST'])
@login_required
def create_team():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('Введіть назву команди', 'danger')
        return redirect(url_for('teams'))

    if Team.query.filter_by(name=name).first():
        flash('Команда з такою назвою вже існує', 'danger')
        return redirect(url_for('teams'))

    team = Team(name=name, description=description, captain_id=current_user.id)
    db.session.add(team)
    team.members.append(current_user)
    db.session.commit()

    flash('Команду створено!', 'success')
    return redirect(url_for('teams'))


@app.route('/api/stats')
def api_stats():
    stats = {
        'total_events': Event.query.filter_by(status='completed').count(),
        'total_waste': float(db.session.query(db.func.sum(Event.waste_collected)).scalar() or 0),
        'total_area': float(db.session.query(db.func.sum(Event.area_cleaned)).scalar() or 0),
        'total_users': User.query.count(),
        'active_teams': Team.query.count()
    }
    return jsonify(stats)


def init_achievements():
    achievements_data = [
        {'name': 'Перші кроки', 'description': 'Участь у першій толоці', 'icon': '🌱', 'type': 'events_count',
         'value': 1},
        {'name': 'Активіст', 'description': 'Участь у 5 толоках', 'icon': '🌿', 'type': 'events_count', 'value': 5},
        {'name': 'Герой чистоти', 'description': 'Участь у 20 толоках', 'icon': '🌳', 'type': 'events_count',
         'value': 20},
        {'name': 'Збирач', 'description': 'Зібрано 10 кг сміття', 'icon': '♻️', 'type': 'waste_collected', 'value': 10},
        {'name': 'Еко-воїн', 'description': 'Зібрано 100 кг сміття', 'icon': '🏆', 'type': 'waste_collected',
         'value': 100},
        {'name': 'Очищувач', 'description': 'Очищено 100 м²', 'icon': '✨', 'type': 'area_cleaned', 'value': 100},
    ]

    for ach_data in achievements_data:
        if not Achievement.query.filter_by(name=ach_data['name']).first():
            achievement = Achievement(
                name=ach_data['name'],
                description=ach_data['description'],
                icon=ach_data['icon'],
                condition_type=ach_data['type'],
                condition_value=ach_data['value']
            )
            db.session.add(achievement)

    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_achievements()

        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@toloka.ua', full_name='Адміністратор')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✓ Створено адміністратора: admin / admin123")

    port = int(os.environ.get('PORT', 5050))
    app.run(debug=True, host='0.0.0.0', port=port)