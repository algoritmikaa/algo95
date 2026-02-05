from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from sqlalchemy.orm import joinedload

app = Flask(__name__)

# Используем переменные окружения для безопасности
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ваш-секретный-ключ-изменяем-позже')

# Для Railway: используем PostgreSQL если есть, иначе SQLite
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images/products'

# Создаем папку для загрузок если её нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    visible_password = db.Column(db.String(80), nullable=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, teacher, student
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    points = db.Column(db.Integer, default=0)
    earned_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    group = db.relationship('Group', backref='students', foreign_keys=[group_id])
    points_history = db.relationship('PointsHistory', backref='user', lazy=True, 
                                     foreign_keys='PointsHistory.user_id')
    orders = db.relationship('Order', backref='student', lazy=True, 
                            foreign_keys='Order.student_id')

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    teacher = db.relationship('User', backref='taught_groups', foreign_keys=[teacher_id])

class PointsHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    changed_by = db.relationship('User', foreign_keys=[changed_by_id])

class RewardReason(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(200), nullable=True)
    price = db.Column(db.Integer, nullable=False)
    original_price = db.Column(db.Integer, nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product')

class Tip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default='Как получить больше баллов?')
    content = db.Column(db.Text, nullable=False, default='''<div style="display: flex; flex-direction: column; gap: 15px;">
                            <div class="tip-card">
                                <div class="tip-icon">
                                    <i class="fas fa-calendar-check"></i>
                                </div>
                                <div>
                                    <h4 style="margin-bottom: 5px; font-size: 1rem;">Регулярное посещение</h4>
                                    <p style="color: var(--text-light); margin-bottom: 0; font-size: 0.9rem;">
                                        +10 баллов за каждый урок
                                    </p>
                                </div>
                            </div>
                            
                            <div class="tip-card">
                                <div class="tip-icon">
                                    <i class="fas fa-clock"></i>
                                </div>
                                <div>
                                    <h4 style="margin-bottom: 5px; font-size: 1rem;">Пунктуальность</h4>
                                    <p style="color: var(--text-light); margin-bottom: 0; font-size: 0.9rem;">
                                        +5 баллов за своевременное прибытие
                                    </p>
                                </div>
                            </div>
                            
                            <div class="tip-card">
                                <div class="tip-icon">
                                    <i class="fas fa-tasks"></i>
                                </div>
                                <div>
                                    <h4 style="margin-bottom: 5px; font-size: 1rem;">Выполнение заданий</h4>
                                    <p style="color: var(--text-light); margin-bottom: 0; font-size: 0.9rem;">
                                        +10 баллов за домашнюю работу
                                    </p>
                                </div>
                            </div>
                            
                            <div class="tip-card">
                                <div class="tip-icon">
                                    <i class="fas fa-star"></i>
                                </div>
                                <div>
                                    <h4 style="margin-bottom: 5px; font-size: 1rem;">Активность на уроке</h4>
                                    <p style="color: var(--text-light); margin-bottom: 0; font-size: 0.9rem;">
                                        +10 баллов за ответы на вопросы
                                    </p>
                                </div>
                            </div>
                        </div>''')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TipItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создаем администратора по умолчанию
def create_default_admin():
    with app.app_context():
        admin_exists = User.query.filter_by(username='admin').first()
        if not admin_exists:
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                first_name='Администратор',
                last_name='Алгоритмики',
                role='admin',
                points=0,
                earned_points=0
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Создан администратор: логин - admin, пароль - admin123")

# Создаем тестовые группы
def create_default_groups():
    with app.app_context():
        groups = [
            'Компьютерная грамотность',
            'Визуальное программирование',
            'Геймдизайн',
            'Создание сайтов',
            'Python Start',
            'Python Pro'
        ]
        
        for group_name in groups:
            group_exists = Group.query.filter_by(name=group_name).first()
            if not group_exists:
                group = Group(name=group_name)
                db.session.add(group)
        
        db.session.commit()
        print("✅ Созданы группы по умолчанию")

# Создаем тестового преподавателя и учеников
def create_test_data():
    with app.app_context():
        teacher = User.query.filter_by(username='teacher').first()
        if not teacher:
            teacher = User(
                username='teacher',
                password=generate_password_hash('teacher123'),
                first_name='Иван',
                last_name='Преподавателев',
                role='teacher',
                points=0,
                earned_points=0
            )
            db.session.add(teacher)
            db.session.commit()
            print("✅ Создан тестовый преподаватель: логин - teacher, пароль - teacher123")
        
        student1 = User.query.filter_by(username='student1').first()
        if not student1:
            student1 = User(
                username='student1',
                password=generate_password_hash('student123'),
                first_name='Алексей',
                last_name='Учеников',
                role='student',
                group_id=1,
                points=100,
                earned_points=100
            )
            db.session.add(student1)
            
            student2 = User(
                username='student2',
                password=generate_password_hash('student123'),
                first_name='Мария',
                last_name='Ученикова',
                role='student',
                group_id=2,
                points=150,
                earned_points=150
            )
            db.session.add(student2)
            db.session.commit()
            print("✅ Созданы тестовые ученики: логин - student1/student2, пароль - student123")
        
        if Product.query.count() == 0:
            products = [
                Product(
                    name='Фирменная футболка Алгоритмика',
                    description='Качественная хлопковая футболка с логотипом школы',
                    image=None,
                    price=200,
                    original_price=200,
                    quantity=10,
                    category='Одежда'
                ),
                Product(
                    name='Кружка с логотипом',
                    description='Керамическая кружка объемом 350 мл',
                    image=None,
                    price=150,
                    original_price=150,
                    quantity=15,
                    category='Сувениры'
                ),
                Product(
                    name='Блокнот программиста',
                    description='Блокнот в твердой обложке, 100 листов',
                    image=None,
                    price=100,
                    original_price=100,
                    quantity=20,
                    category='Канцелярия'
                ),
                Product(
                    name='Набор стикеров',
                    description='Набор стикеров с персонажами Алгоритмики',
                    image=None,
                    price=50,
                    original_price=50,
                    quantity=30,
                    category='Сувениры'
                )
            ]
            
            for product in products:
                db.session.add(product)
            
            db.session.commit()
            print("✅ Созданы тестовые товары")
        
        if RewardReason.query.count() == 0:
            reasons = [
                {'reason': 'Посещение урока', 'points': 10, 'order': 1},
                {'reason': 'Пунктуальность', 'points': 5, 'order': 2},
                {'reason': 'Ответы на вопросы', 'points': 10, 'order': 3},
                {'reason': 'Выполнение заданий на уроке', 'points': 10, 'order': 4},
                {'reason': 'Домашнее задание', 'points': 10, 'order': 5},
                {'reason': 'Индивидуальный проект', 'points': 10, 'order': 6}
            ]
            
            for reason_data in reasons:
                reason = RewardReason(
                    reason=reason_data['reason'],
                    points=reason_data['points'],
                    order=reason_data['order']
                )
                db.session.add(reason)
            
            db.session.commit()
            print("✅ Созданы причины начисления баллов")
        
        if Tip.query.count() == 0:
            tip = Tip()
            db.session.add(tip)
            db.session.commit()
            print("✅ Создан начальный текст советов")
        
        if TipItem.query.count() == 0:
            tips = [
                TipItem(reason='Регулярное посещение уроков', points=10),
                TipItem(reason='Пунктуальность', points=5),
                TipItem(reason='Активная работа на уроке', points=10),
                TipItem(reason='Выполнение домашних заданий', points=10),
                TipItem(reason='Участие в проектах', points=15),
                TipItem(reason='Помощь другим ученикам', points=10)
            ]
            
            for tip in tips:
                db.session.add(tip)
            
            db.session.commit()
            print("✅ Созданы советы для учеников")

# Создаем БД и тестовые данные при запуске
with app.app_context():
    db.create_all()
    create_default_admin()
    create_default_groups()
    create_test_data()
    print("✅ База данных и тестовые данные созданы")

# Главная страница
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        
        flash('Неверный логин или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ========== АДМИНИСТРАТОР ==========

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    stats = {
        'total_users': User.query.count(),
        'total_students': User.query.filter_by(role='student').count(),
        'total_teachers': User.query.filter_by(role='teacher').count(),
        'total_products': Product.query.count(),
        'pending_orders': Order.query.filter_by(status='pending').count()
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    users = User.query.all()
    groups = Group.query.all()
    return render_template('admin/users.html', users=users, groups=groups)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
def create_users():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            users_created = 0
            
            for i in range(1, 11):
                username = request.form.get(f'username_{i}')
                if username and username.strip():
                    password = request.form.get(f'password_{i}')
                    first_name = request.form.get(f'first_name_{i}')
                    last_name = request.form.get(f'last_name_{i}')
                    role = request.form.get(f'role_{i}')
                    group_id = request.form.get(f'group_id_{i}')
                    
                    if password and first_name and last_name and role:
                        existing_user = User.query.filter_by(username=username.strip()).first()
                        if existing_user:
                            flash(f'Пользователь с логином {username} уже существует', 'warning')
                            continue
                        
                        user = User(
                            username=username.strip(),
                            password=generate_password_hash(password),
                            visible_password=password,
                            first_name=first_name.strip(),
                            last_name=last_name.strip(),
                            role=role,
                            group_id=int(group_id) if group_id else None,
                            points=0,
                            earned_points=0
                        )
                        db.session.add(user)
                        users_created += 1
            
            db.session.commit()
            
            if users_created > 0:
                flash(f'Успешно создано {users_created} пользователей', 'success')
            else:
                flash('Не создано ни одного пользователя. Проверьте заполнение полей.', 'warning')
            
            return redirect(url_for('admin_users'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании пользователей: {str(e)}', 'error')
    
    groups = Group.query.order_by(Group.name).all()
    return render_template('admin/create_users.html', groups=groups)

@app.route('/admin/users/<int:user_id>', methods=['GET', 'POST'])
@app.route('/teacher/students/<int:user_id>', methods=['GET', 'POST'])
@login_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    if current_user.role == 'admin':
        pass
    elif current_user.role == 'teacher':
        if not user.group or user.group.teacher_id != current_user.id:
            flash('У вас нет доступа к этому ученику', 'error')
            return redirect(url_for('teacher_dashboard'))
    else:
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        if 'update_info' in request.form:
            user.first_name = request.form['first_name']
            user.last_name = request.form['last_name']
            user.username = request.form['username']
            
            new_password = request.form.get('new_password', '')
            if new_password:
                user.visible_password = new_password
                user.password = generate_password_hash(new_password)
            
            if current_user.role == 'admin':
                user.role = request.form['role']
                user.group_id = request.form['group_id'] if request.form['group_id'] else None
            
            db.session.commit()
            flash('Информация обновлена', 'success')
        
        elif 'add_points' in request.form:
            points = int(request.form['points'])
            reason = request.form['reason']
            
            user.points += points
            user.earned_points += points
            
            history = PointsHistory(
                user_id=user.id,
                points_change=points,
                reason=reason,
                changed_by_id=current_user.id
            )
            db.session.add(history)
            db.session.commit()
            
            flash(f'Начислено {points} баллов', 'success')
        
        elif 'remove_points' in request.form:
            points = int(request.form['points'])
            reason = request.form['reason']
            
            if user.points >= points:
                user.points -= points
                
                history = PointsHistory(
                    user_id=user.id,
                    points_change=-points,
                    reason=reason,
                    changed_by_id=current_user.id
                )
                db.session.add(history)
                db.session.commit()
                
                flash(f'Списано {points} баллов', 'success')
            else:
                flash('Недостаточно баллов', 'error')
        
        elif 'delete_user' in request.form and current_user.role == 'admin':
            try:
                PointsHistory.query.filter_by(user_id=user.id).delete()
                Order.query.filter_by(student_id=user.id).delete()
                
                if user.role == 'teacher':
                    groups = Group.query.filter_by(teacher_id=user.id).all()
                    for group in groups:
                        group.teacher_id = None
                
                db.session.delete(user)
                db.session.commit()
                
                flash(f'Пользователь {user.first_name} {user.last_name} успешно удален', 'success')
                return redirect(url_for('admin_users'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при удалении пользователя: {str(e)}', 'error')
    
    history = PointsHistory.query.filter_by(user_id=user.id).order_by(PointsHistory.created_at.desc()).all()
    groups = Group.query.all()
    reward_reasons = RewardReason.query.order_by(RewardReason.order).all()
    
    if current_user.role == 'admin':
        template = 'admin/user_detail.html'
    else:
        template = 'teacher/student_detail.html'
    
    return render_template(template, user=user, groups=groups, history=history, reward_reasons=reward_reasons)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Вы не можете удалить свой собственный аккаунт', 'error')
        return redirect(url_for('user_detail', user_id=user_id))
    
    try:
        PointsHistory.query.filter_by(user_id=user.id).delete()
        Order.query.filter_by(student_id=user.id).delete()
        
        if user.role == 'teacher':
            groups = Group.query.filter_by(teacher_id=user.id).all()
            for group in groups:
                group.teacher_id = None
        
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Пользователь {user.first_name} {user.last_name} успешно удален', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/groups')
@login_required
def admin_groups():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    groups = Group.query.all()
    teachers = User.query.filter_by(role='teacher').all()
    return render_template('admin/groups.html', groups=groups, teachers=teachers)

@app.route('/admin/groups/create', methods=['GET', 'POST'])
@login_required
def create_group():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name']
        teacher_id = request.form['teacher_id'] if request.form['teacher_id'] else None
        
        group = Group(name=name, teacher_id=teacher_id)
        db.session.add(group)
        db.session.commit()
        
        flash('Группа создана', 'success')
        return redirect(url_for('admin_groups'))
    
    teachers = User.query.filter_by(role='teacher').all()
    return render_template('admin/create_group.html', teachers=teachers)

@app.route('/admin/groups/<int:group_id>', methods=['GET', 'POST'])
@login_required
def group_detail(group_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    group = Group.query.get_or_404(group_id)
    teachers = User.query.filter_by(role='teacher').all()
    
    if request.method == 'POST':
        if 'update_group' in request.form:
            group.name = request.form['name']
            group.teacher_id = request.form['teacher_id'] if request.form['teacher_id'] else None
            db.session.commit()
            flash('Информация обновлена', 'success')
        
        elif 'delete_group' in request.form:
            try:
                User.query.filter_by(group_id=group_id).update({'group_id': None})
                db.session.delete(group)
                db.session.commit()
                
                flash('Группа успешно удалена', 'success')
                return redirect(url_for('admin_groups'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при удалении группы: {str(e)}', 'error')
    
    students = User.query.filter_by(group_id=group_id, role='student').order_by(User.earned_points.desc()).all()
    
    for i, student in enumerate(students, 1):
        student.rating_position = i
    
    return render_template('admin/group_detail.html', group=group, teachers=teachers, students=students)

@app.route('/admin/groups/delete/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    group = Group.query.get_or_404(group_id)
    
    try:
        User.query.filter_by(group_id=group_id).update({'group_id': None})
        db.session.delete(group)
        db.session.commit()
        
        flash('Группа успешно удалена', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении группы: {str(e)}', 'error')
    
    return redirect(url_for('admin_groups'))

@app.route('/admin/shop')
@login_required
def admin_shop():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    products = Product.query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]
    
    return render_template('admin/shop_admin.html', products=products, categories=categories)

@app.route('/admin/shop/product/<int:product_id>', methods=['GET', 'POST'])
@app.route('/admin/shop/product/new', methods=['GET', 'POST'])
@login_required
def product_detail(product_id=None):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    if product_id:
        product = Product.query.get_or_404(product_id)
    else:
        product = None
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        
        # ИСПРАВЛЕНИЕ 1: Безопасное преобразование цены
        price_str = request.form.get('price', '').strip()
        if price_str and price_str.isdigit():
            price = int(price_str)
        else:
            flash('Цена должна быть числом', 'error')
            return render_template('admin/product_detail.html', product=product)
        
        # ИСПРАВЛЕНИЕ 2: Безопасное преобразование количества
        quantity_str = request.form.get('quantity', '').strip()
        if quantity_str and quantity_str.isdigit():
            quantity = int(quantity_str)
        else:
            flash('Количество должно быть числом', 'error')
            return render_template('admin/product_detail.html', product=product)
        
        category = request.form['category']
        
        # ИСПРАВЛЕНИЕ 3: Обработка оригинальной цены
        original_price_str = request.form.get('original_price', '').strip()
        if original_price_str and original_price_str.isdigit():
            original_price = int(original_price_str)
        else:
            original_price = price  # Если не указана, равна цене со скидкой
        
        # Проверка: цена со скидкой не может быть больше оригинальной
        if price > original_price:
            flash('Цена со скидкой не может быть больше оригинальной', 'error')
            return render_template('admin/product_detail.html', product=product)
        
        # Обработка загрузки изображения
        image_file = request.files.get('image')
        image_filename = None
        
        if image_file and image_file.filename:
            # Создаем папку для загрузок, если её нет
            os.makedirs('static/images/products', exist_ok=True)
            
            filename = secure_filename(image_file.filename)
            image_path = os.path.join('static/images/products', filename)
            image_file.save(image_path)
            image_filename = f'static/images/products/{filename}'
        
        if product:
            # Обновляем существующий товар
            product.name = name
            product.description = description
            product.price = price
            product.original_price = original_price
            product.quantity = quantity
            product.category = category
            if image_filename:
                product.image = image_filename
        else:
            # Создаем новый товар
            product = Product(
                name=name,
                description=description,
                price=price,
                original_price=original_price,
                quantity=quantity,
                category=category,
                image=image_filename
            )
            db.session.add(product)
        
        try:
            db.session.commit()
            
            if product_id:
                flash('Товар обновлен', 'success')
            else:
                flash('Товар создан', 'success')
            
            return redirect(url_for('admin_shop'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении товара: {str(e)}', 'error')
            return render_template('admin/product_detail.html', product=product)
    
    return render_template('admin/product_detail.html', product=product)

@app.route('/admin/orders')
@login_required
def admin_orders():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_detail(order_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        if 'complete' in request.form:
            order.status = 'completed'
            db.session.commit()
            flash('Заказ отмечен как выданный', 'success')
        
        elif 'cancel' in request.form:
            order.student.points += order.product.price * order.quantity
            order.product.quantity += order.quantity
            order.status = 'cancelled'
            
            db.session.commit()
            flash('Заказ отменен', 'success')
    
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/shop/product/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    
    flash('Товар удален', 'success')
    return redirect(url_for('admin_shop'))

@app.route('/admin/reward_reasons')
@login_required
def admin_reward_reasons():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    reasons = RewardReason.query.order_by(RewardReason.order, RewardReason.created_at.desc()).all()
    return render_template('admin/reward_reasons.html', reasons=reasons)

@app.route('/admin/reward_reasons/update_order', methods=['POST'])
@login_required
def update_reward_reasons_order():
    if current_user.role != 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        data = request.json
        for item in data:
            reason = RewardReason.query.get(item['id'])
            if reason:
                reason.order = item['order']
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Порядок сохранен'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/reward_reasons/create', methods=['GET', 'POST'])
@login_required
def create_reward_reason():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        reason_text = request.form['reason']
        points = int(request.form['points'])
        
        max_order = db.session.query(db.func.max(RewardReason.order)).scalar() or 0
        next_order = max_order + 1
        
        reward_reason = RewardReason(reason=reason_text, points=points, order=next_order)
        db.session.add(reward_reason)
        db.session.commit()
        
        flash(f'Причина "{reason_text}" создана с начислением {points} баллов', 'success')
        return redirect(url_for('admin_reward_reasons'))
    
    max_order = db.session.query(db.func.max(RewardReason.order)).scalar() or 0
    next_order = max_order + 1
    
    return render_template('admin/create_reward_reason.html', next_order=next_order)

@app.route('/admin/reward_reasons/<int:reason_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_reward_reason(reason_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    reason = RewardReason.query.get_or_404(reason_id)
    
    if request.method == 'POST':
        reason.reason = request.form['reason']
        reason.points = int(request.form['points'])
        
        db.session.commit()
        flash('Причина обновлена', 'success')
        return redirect(url_for('admin_reward_reasons'))
    
    return render_template('admin/edit_reward_reason.html', reason=reason)

@app.route('/admin/reward_reasons/<int:reason_id>/delete', methods=['POST'])
@login_required
def delete_reward_reason(reason_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    reason = RewardReason.query.get_or_404(reason_id)
    db.session.delete(reason)
    db.session.commit()
    
    flash('Причина удалена', 'success')
    return redirect(url_for('admin_reward_reasons'))

@app.route('/admin/old_tips')
@login_required
def admin_old_tips():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    tip = Tip.query.first()
    if not tip:
        tip = Tip()
        db.session.add(tip)
        db.session.commit()
    
    return render_template('admin/old_tips.html', tip=tip)

@app.route('/admin/old_tips/edit', methods=['POST'])
@login_required
def edit_old_tips():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    tip = Tip.query.first()
    if not tip:
        tip = Tip()
        db.session.add(tip)
    
    tip.title = request.form['title']
    tip.content = request.form['content']
    
    db.session.commit()
    flash('Советы (старые) обновлены', 'success')
    return redirect(url_for('admin_old_tips'))

@app.route('/admin/tips')
@login_required
def admin_tips():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    tips = TipItem.query.order_by(TipItem.created_at.desc()).all()
    return render_template('admin/tips.html', tips=tips)

@app.route('/admin/tips/add', methods=['POST'])
@login_required
def add_tip_item():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    reason = request.form['reason']
    points = int(request.form['points'])
    
    tip = TipItem(reason=reason, points=points)
    db.session.add(tip)
    db.session.commit()
    
    flash(f'Причина "{reason}" добавлена с начислением {points} баллов', 'success')
    return redirect(url_for('admin_tips'))

@app.route('/admin/tips/edit/<int:tip_id>', methods=['POST'])
@login_required
def edit_tip_item(tip_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    tip = TipItem.query.get_or_404(tip_id)
    
    tip.reason = request.form['reason']
    tip.points = int(request.form['points'])
    
    db.session.commit()
    flash('Совет обновлен', 'success')
    return redirect(url_for('admin_tips'))

@app.route('/admin/tips/delete/<int:tip_id>', methods=['POST'])
@login_required
def delete_tip_item(tip_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    tip = TipItem.query.get_or_404(tip_id)
    db.session.delete(tip)
    db.session.commit()
    
    flash('Причина удалена', 'success')
    return redirect(url_for('admin_tips'))

# ========== ПРЕПОДАВАТЕЛЬ ==========

@app.route('/teacher')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    groups = Group.query.filter_by(teacher_id=current_user.id).all()
    
    total_students = 0
    for group in groups:
        student_count = User.query.filter_by(group_id=group.id, role='student').count()
        total_students += student_count
    
    return render_template('teacher/dashboard.html', groups=groups, total_students=total_students)

@app.route('/teacher/students', methods=['GET', 'POST'])
@login_required
def teacher_students():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    groups = Group.query.filter_by(teacher_id=current_user.id).all()
    
    for group in groups:
        group.student_count = User.query.filter_by(group_id=group.id, role='student').count()
    
    if not groups:
        flash('У вас нет назначенных групп', 'warning')
        return render_template('teacher/teacher_students_new.html', students=[], groups=[], selected_group=None, reward_reasons=[])
    
    selected_group_id = request.args.get('group_id')
    selected_group = None
    students = []
    
    if selected_group_id:
        try:
            selected_group_id = int(selected_group_id)
            selected_group = Group.query.get(selected_group_id)
            if selected_group and selected_group.teacher_id == current_user.id:
                students = User.query.filter_by(group_id=selected_group_id, role='student').order_by(User.earned_points.desc()).all()
                for i, student in enumerate(students, 1):
                    student.rating_position = i
            else:
                flash('У вас нет доступа к этой группе', 'error')
        except Exception as e:
            flash(f'Ошибка загрузки группы: {str(e)}', 'error')
    
    reward_reasons = RewardReason.query.order_by(RewardReason.order).all()
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            students_updated = 0
            total_points = 0
            
            for student_id, reasons in data.items():
                student = User.query.get(int(student_id))
                
                if student and student.group and student.group.teacher_id == current_user.id:
                    student_points = 0
                    student_reasons = []
                    
                    for reason_data in reasons:
                        reason = RewardReason.query.get(reason_data['reason_id'])
                        if reason:
                            student_points += reason.points
                            student_reasons.append(reason.reason)
                    
                    if student_points > 0:
                        student.points += student_points
                        student.earned_points += student_points
                        
                        history = PointsHistory(
                            user_id=student.id,
                            points_change=student_points,
                            reason='Массовое начисление: ' + ', '.join(student_reasons),
                            changed_by_id=current_user.id
                        )
                        db.session.add(history)
                        
                        students_updated += 1
                        total_points += student_points
            
            if students_updated > 0:
                db.session.commit()
                message = f'Успешно начислено {total_points} баллов {students_updated} ученикам'
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': 'Не выбрано ни одной причины для начисления'}), 400
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Ошибка: {str(e)}'}), 500
    
    return render_template('teacher/teacher_students_new.html', 
                         students=students, 
                         groups=groups, 
                         selected_group=selected_group,
                         reward_reasons=reward_reasons)

@app.route('/teacher/group/<int:group_id>')
@login_required
def teacher_group_detail(group_id):
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    group = Group.query.get_or_404(group_id)
    if group.teacher_id != current_user.id:
        flash('У вас нет доступа к этой группе', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    students = User.query.filter_by(group_id=group_id, role='student').order_by(User.earned_points.desc()).all()
    
    for i, student in enumerate(students, 1):
        student.rating_position = i
    
    return render_template('teacher/group_detail.html', group=group, students=students)

@app.route('/teacher/shop')
@login_required
def teacher_shop():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    products = Product.query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]
    
    return render_template('teacher/shop.html', products=products, categories=categories)

# ========== УЧЕНИК ==========

@app.route('/student')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    history = PointsHistory.query.filter_by(user_id=current_user.id).order_by(PointsHistory.created_at.desc()).limit(10).all()
    tip = Tip.query.first()
    
    return render_template('student/dashboard.html', history=history, tip=tip)

@app.route('/student/shop')
@login_required
def student_shop():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    products = Product.query.filter(Product.quantity > 0).all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]
    
    return render_template('student/shop.html', products=products, categories=categories)

@app.route('/student/shop/buy/<int:product_id>', methods=['POST'])
@login_required
def buy_product(product_id):
    if current_user.role != 'student':
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    product = Product.query.get_or_404(product_id)
    
    if product.quantity < 1:
        return jsonify({'error': 'Товар закончился'}), 400
    
    if current_user.points < product.price:
        return jsonify({'error': 'Недостаточно баллов'}), 400
    
    order = Order(
        student_id=current_user.id,
        product_id=product.id,
        quantity=1,
        status='pending'
    )
    
    current_user.points -= product.price
    product.quantity -= 1
    
    db.session.add(order)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Товар куплен!', 
        'new_balance': current_user.points,
        'order_id': order.id
    })

@app.route('/student/profile')
@login_required
def student_profile():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    history = PointsHistory.query.filter_by(user_id=current_user.id).order_by(PointsHistory.created_at.desc()).all()
    
    rating_position = None
    if current_user.group_id:
        group_students = User.query.filter_by(
            group_id=current_user.group_id, 
            role='student'
        ).order_by(User.earned_points.desc()).all()
        
        for i, student in enumerate(group_students, 1):
            if student.id == current_user.id:
                rating_position = i
                break
    
    tips = TipItem.query.order_by(TipItem.created_at.desc()).all()
    
    return render_template('student/profile.html', history=history, rating_position=rating_position, tips=tips)

@app.route('/student/group_rating')
@login_required
def student_group_rating():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    if not current_user.group_id:
        flash('Вы не состоите в группе', 'warning')
        return redirect(url_for('student_dashboard'))
    
    students = User.query.filter_by(
        group_id=current_user.group_id, 
        role='student'
    ).order_by(User.earned_points.desc()).all()
    
    for i, student in enumerate(students, 1):
        student.rating_position = i
    
    group = Group.query.get(current_user.group_id)
    
    return render_template('student/group_rating.html', students=students, group=group)

@app.route('/api/filter/students')
@login_required
def filter_students():
    group_id = request.args.get('group_id')
    
    if group_id:
        students = User.query.filter_by(group_id=group_id, role='student').all()
    else:
        students = User.query.filter_by(role='student').all()
    
    result = []
    for student in students:
        result.append({
            'id': student.id,
            'name': f'{student.first_name} {student.last_name}',
            'group': student.group.name if student.group else 'Без группы',
            'points': student.points,
            'earned_points': student.earned_points
        })
    
    return jsonify(result)

@app.context_processor
def inject_now():
    return {'datetime': datetime}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)