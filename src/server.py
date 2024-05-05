from flask import Flask, render_template, request, redirect, url_for, flash, make_response,jsonify
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import uuid
from flask import send_from_directory
import os
import secrets
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# MySQL connection details
mysql_config = {
    'user': '1testing123',
    'password': '179okan789bruh',
    'host': '1testing123.mysql.pythonanywhere-services.com',
    'database': '1testing123$default'
}
categories = ['Bütün kategoriler','Python','HTML5',"CSS","JavaScript"]
# Email settings
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'okannn123123@gmail.com'
app.config['MAIL_PASSWORD'] = 'uqoz wzzs ethn kcvo'

mail = Mail(app)

def connect_db():
    return mysql.connector.connect(**mysql_config)

def execute_query(query, values=(), fetch_result=False):
    cnx = connect_db()
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(query, values)
    if fetch_result:
        result = cursor.fetchall()
    else:
        result = None
    cnx.commit()
    cursor.close()
    cnx.close()
    return result
def secure_filename(filename):
    """
    Return a secure version of the filename.
    """
    _, ext = os.path.splitext(filename)
    return str(uuid.uuid4()) + ext.lower()
def generate_verification_token():
    return secrets.token_urlsafe(16)

def send_verification_email(email, verification_token):
    verification_link = url_for('verify_email', verification_token=verification_token, _external=True)
    msg = Message('Verify Your Email', sender='your_email@example.com', recipients=[email])
    msg.body = f'Click the following link to verify your email: {verification_link}'
    mail.send(msg)

def set_user_cookie(user_id):
    # Generate a unique and difficult-to-predict cookie for the user
    user_cookie = str(uuid.uuid4())

    # Set the user's unique cookie in the database
    query = "UPDATE users SET user_cookie = %s WHERE id = %s"
    execute_query(query, (user_cookie, user_id,), fetch_result=False)

    return user_cookie
def is_own(user_id, question_id):
    # Kullanıcı ilanın sahibi mi kontrol etmek için veritabanından ilanın sahibiyle karşılaştır
    query = "SELECT user_id FROM questions WHERE id = %s"
    result = execute_query(query, (question_id,), fetch_result=True)

    if result:
        return result[0]['user_id'] == user_id
    else:
        return False  # Eğer ilan bulunamazsa False döndür
def get_userid_from_cookie(cookie):
    query = "SELECT id FROM users WHERE user_cookie = %s"
    result = execute_query(query, (cookie,), fetch_result=True)

    if result:
        return result[0]["id"]
    else:
        return False
@app.route('/question/<int:id>')
def question(id):
    query = "SELECT * FROM questions WHERE id = %s"
    question = execute_query(query, (id,), fetch_result=True)
    logged=False
    is_own2=False
    try:
        current_user_id=get_userid_from_cookie(request.cookies["user_cookie"])
        is_own2=is_own(current_user_id,question[0]["id"])
        logged=True
    except:
        pass

    if question:
        user_id = question[0]['user_id']
        answers_query = "SELECT * FROM answers WHERE question_id = %s"
        answers = execute_query(answers_query, (id,), fetch_result=True)

        # Soruyu cevaplayan kullanıcının bilgilerini al
        question_user_data = get_userdata(user_id)

        # Cevaplayan kullanıcıların bilgilerini al ve her bir cevaba ekleyin
        for answer in answers:
            answer_user_data = get_userdata(answer['user_id'])
            answer['user_data'] = answer_user_data

        return render_template('question.html',is_own1=is_own2, question=question[0], data=question_user_data, answers=answers, max_answers_reached=len(answers) >= 2)
    else:
        # Verilen ID'ye sahip soru bulunamadı
        return "Soru bulunamadı", 404



def get_userdata(user_id):
    query = "SELECT image_link, username FROM users WHERE id = %s"
    user = execute_query(query, (user_id,), fetch_result=True)
    if user:
        return user[0]
    else:
        return None


@app.route('/')
def index():
    # Kullanıcının cookie'sinden kullanıcı bilgilerini al
    user_cookie = request.cookies.get('user_cookie')
    if user_cookie:
        query = "SELECT * FROM users WHERE user_cookie = %s"
        result = execute_query(query, (user_cookie,), fetch_result=True)
        if result:
            user = result[0]
    else:
        user = None

    # Tüm soruları al, en son eklenenler ilk sırada olacak şekilde
    category = request.args.get("category")
    if category and category!="Bütün kategoriler":
        query = "SELECT * FROM questions WHERE category = %s ORDER BY id DESC"
        category_questions = execute_query(query, (category,), fetch_result=True)
        return render_template('home.html', current_user=user, questions=category_questions, selected_category=category, categories=categories,current_category=category)
    else:
        query = "SELECT * FROM questions ORDER BY id DESC"
        questions = execute_query(query, fetch_result=True)
        return render_template('home.html', current_user=user, questions=questions, categories=categories,current_category="Bütün kategoriler")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if email address is already registered
        query = "SELECT * FROM users WHERE email = %s"
        result = execute_query(query, (email,), fetch_result=True)
        if result:
            flash('This email address is already registered.', 'danger')
            return redirect(url_for('signup'))

        # Check if username is already taken
        query = "SELECT * FROM users WHERE username = %s"
        result = execute_query(query, (username,), fetch_result=True)
        if result:
            flash('This username is already taken. Please choose another one.', 'danger')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        verification_token = generate_verification_token()
        query = "INSERT INTO users (username, email, password, verification_token) VALUES (%s, %s, %s, %s)"
        values = (username, email, hashed_password, verification_token)
        execute_query(query, values, fetch_result=False)

        # Send verification email with the verification link
        send_verification_email(email, verification_token)

        # Get the user ID after inserting into database
        query = "SELECT id FROM users WHERE email = %s"
        result = execute_query(query, (email,), fetch_result=True)
        if result:
            user_id = result[0]['id']
            # Generate and set the user cookie
            user_cookie = set_user_cookie(user_id)

            # Set the user's unique cookie in the response
            response = make_response(redirect(url_for('login')))
            response.set_cookie('user_cookie', user_cookie)

            flash('Verification email has been sent. Please check your email to complete registration.', 'success')
            return response
        else:
            flash('An error occurred while signing up. Please try again later.', 'danger')
            return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    # Kullanıcının cookie'sini sil
    response = make_response(redirect(url_for('login')))
    response.set_cookie('user_cookie', expires=0)
    flash('You have been logged out.', 'success')
    return response

@app.route('/verify/<string:verification_token>')
def verify_email(verification_token):
    query = "SELECT * FROM users WHERE verification_token = %s"
    result = execute_query(query, (verification_token,), fetch_result=True)
    if result:
        user_id = result[0]['id']
        query = "UPDATE users SET verified = true, verification_token = NULL WHERE id = %s"
        execute_query(query, (user_id,), fetch_result=False)
        flash('Your email has been verified. You can now log in.', 'success')
    else:
        flash('Invalid verification link. Please try again.', 'danger')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        query = "SELECT * FROM users WHERE username = %s"
        result = execute_query(query, (username,), fetch_result=True)
        if result:
            user = result[0]
            if check_password_hash(user['password'], password):
                if user['verified']:
                    # Kullanıcı girişi başarılı, özel cookie oluştur
                    user_cookie = set_user_cookie(user['id'])

                    # Set the user's unique cookie in the response
                    response = make_response(redirect(url_for('index')))
                    response.set_cookie('user_cookie', user_cookie)

                    flash('Login successful!', 'success')
                    return response
                else:
                    flash('Please verify your email address to login.', 'warning')
            else:
                flash('Invalid username or password.', 'danger')
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')
@app.route('/select_best_answer', methods=['POST'])
def select_best_answer():
    # Kullanıcının cookie'sinden kullanıcı bilgilerini al
    user_cookie = request.cookies.get('user_cookie')
    if user_cookie:
        query = "SELECT * FROM users WHERE user_cookie = %s"
        result = execute_query(query, (user_cookie,), fetch_result=True)
        if result:
            user_id = result[0]['id']
            answer_id = request.form['answer_id']
            question_id = request.form['question_id']

            # Soruyu veritabanından al
            query = "SELECT * FROM questions WHERE id = %s"
            question = execute_query(query, (question_id,), fetch_result=True)

            if question:
                # Soruyu soran kullanıcı mı?
                if user_id == question[0]['user_id']:
                    # Sorunun en iyi cevabını belirle
                    query = "UPDATE answers SET is_best_answer = CASE WHEN id = %s THEN true ELSE false END WHERE question_id = %s"
                    execute_query(query, (answer_id, question_id,), fetch_result=False)

                    flash('En iyi cevap seçildi.', 'success')
                    return redirect(url_for('question', id=question_id))
                else:
                    flash('Bu işlemi yapmak için yetkiniz yok.', 'danger')
                    return redirect(url_for('question', id=question_id))
            else:
                # Verilen ID'ye sahip soru bulunamadı
                flash('Soru bulunamadı.', 'danger')
                return redirect(url_for('index'))
        else:
            # Geçerli bir kullanıcı bulunamadı
            flash('Geçersiz kullanıcı.', 'danger')
            return redirect(url_for('index'))
    else:
        # Kullanıcı girişi yapılmamış
        flash('Kullanıcı girişi yapmadınız.', 'danger')
        return redirect(url_for('login'))

@app.route('/ask_question', methods=['GET'])
def show_ask_question_form():
    b=request.args.get("b")
    return render_template('ask_question.html',baslik=b)
@app.route('/cevap_ver', methods=['POST'])
def cevap_ver():
    # Kullanıcının cookie'sinden kullanıcı bilgilerini al
    user_cookie = request.cookies.get('user_cookie')
    if user_cookie:
        query = "SELECT * FROM users WHERE user_cookie = %s"
        result = execute_query(query, (user_cookie,), fetch_result=True)
        if result:
            user_id = result[0]['id']
            content = request.form['content']
            image = request.files['image'] if 'image' in request.files else None
            question_id = request.form['question_id']

            # Soruyu veritabanından al
            query = "SELECT * FROM questions WHERE id = %s"
            question = execute_query(query, (question_id,), fetch_result=True)

            if question:
                # Soruya ait mevcut cevap sayısını kontrol et
                query = "SELECT COUNT(*) FROM answers WHERE question_id = %s"
                count = execute_query(query, (question_id,), fetch_result=True)
                if count and count[0]['COUNT(*)'] < 2:
                    # Kullanıcının daha önce bu soruya cevap verip vermediğini kontrol et
                    query = "SELECT * FROM answers WHERE user_id = %s AND question_id = %s"
                    result = execute_query(query, (user_id, question_id), fetch_result=True)
                    if result:
                        flash('Bu soruya zaten cevap verdiniz.', 'danger')
                        return redirect(url_for('question', id=question_id))

                    # Kullanıcının kendi sorusuna cevap vermesini engelle
                    if user_id == question[0]['user_id']:
                        flash('Kendi sorunuz için cevap veremezsiniz.', 'danger')
                        return redirect(url_for('question', id=question_id))

                    # Resmi assets klasörüne kaydet
                    if image:
                        filename = secure_filename(image.filename)
                        image_path = os.path.join(app.root_path, 'assets', filename)
                        image.save(image_path)

                    # Cevabı veritabanına kaydet
                    query = "INSERT INTO answers (question_id, user_id, content, image_link) VALUES (%s, %s, %s, %s)"
                    values = (question_id, user_id, content, filename if image else None)
                    execute_query(query, values, fetch_result=False)

                    flash('Cevabınız başarıyla gönderildi.', 'success')
                    return redirect(url_for('question', id=question_id))
                else:
                    flash('Bu soruya maksimum iki cevap verilebilir.', 'danger')
                    return redirect(url_for('question', id=question_id))
            else:
                # Verilen ID'ye sahip soru bulunamadı
                flash('Soru bulunamadı.', 'danger')
                return redirect(url_for('index'))
        else:
            # Geçerli bir kullanıcı bulunamadı
            flash('Geçersiz kullanıcı.', 'danger')
            return redirect(url_for('index'))
    else:
        # Kullanıcı girişi yapılmamış
        flash('Kullanıcı girişi yapmadınız.', 'danger')
        return redirect(url_for('login'))







@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if request.method == 'POST':
        user_cookie = request.cookies.get('user_cookie')
        if user_cookie:
            query = "SELECT * FROM users WHERE user_cookie = %s"
            result = execute_query(query, (user_cookie,), fetch_result=True)
            if result:
                user_id = result[0]['id']
                new_username = request.form['username']
                new_profile_picture = request.files['profile_picture']

                # Profil resmi değiştirilmişse yeni dosyayı kaydet
                if new_profile_picture.filename != '':
                    filename = secure_filename(new_profile_picture.filename)
                    profile_picture_path = os.path.join(app.root_path, 'profile_pictures', filename)
                    new_profile_picture.save(profile_picture_path)
                    # Profil resmi yolunu güncelle
                    query = "UPDATE users SET image_link = %s WHERE id = %s"
                    execute_query(query, (filename, user_id,), fetch_result=False)

                # Kullanıcı adını güncelle
                query = "UPDATE users SET username = %s WHERE id = %s"
                execute_query(query, (new_username, user_id,), fetch_result=False)

                flash('Profile updated successfully!', 'success')
                return redirect("/")
        flash('You must be logged in to edit your profile.', 'danger')
        return redirect(url_for('login'))
    else:
        user_cookie = request.cookies.get('user_cookie')
        if user_cookie:
            query = "SELECT * FROM users WHERE user_cookie = %s"
            result = execute_query(query, (user_cookie,), fetch_result=True)
            if result:
                current_user = result[0]
                return render_template('edit_profile.html', current_user=current_user)
        flash('You must be logged in to edit your profile.', 'danger')
        return redirect(url_for('login'))



@app.route('/ask_question', methods=['POST'])
def ask_question():
    user_cookie = request.cookies.get('user_cookie')
    if user_cookie:
        query = "SELECT * FROM users WHERE user_cookie = %s"
        result = execute_query(query, (user_cookie,), fetch_result=True)
        if result:
            user_id = result[0]['id']
            user_points = result[0]['puan']

            # Kullanıcının puanını kontrol et ve yeterli ise işlem yap
            if user_points >= 10:
                title = request.form['title']
                content = request.form['content']
                category = request.form['category']  # Kategori bilgisini al

                # Resmi al
                image = request.files['image']

                # Resmi assets klasörüne kaydet
                if image.filename != '':
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.root_path, 'assets', filename)
                    image.save(image_path)

                # Kullanıcının puanını güncelle
                query = "UPDATE users SET puan = puan - 10 WHERE id = %s"
                execute_query(query, (user_id,), fetch_result=False)

                query = "INSERT INTO questions (user_id, title, content, category, image_link) VALUES (%s, %s, %s, %s, %s)"
                values = (user_id, title, content, category, filename if image.filename != '' else None)
                execute_query(query, values, fetch_result=False)

                flash('Your question has been posted successfully!', 'success')
                return redirect(url_for('index'))
            else:
                flash('You do not have enough points to ask a question.', 'danger')
                return redirect(url_for('index'))  # Ya da başka bir sayfaya yönlendirme yapabilirsiniz.
    flash('You must be logged in to ask a question.', 'danger')
    return redirect(url_for('login'))


@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory('assets', filename)

@app.route('/profile_pictures/<path:filename>')
def profile_pictures(filename):
    return send_from_directory('profile_pictures', filename)

@app.route("/hakkimizda")
def hakkimizda():
    return render_template("hakkimizda.html")
@app.route("/subject/<int:id>")
def subjects(id):
    # İlgili testleri sorgula
    questions = execute_query("SELECT * FROM tests WHERE subject_id = %s", (id,), fetch_result=True)

    # Konunun dilini al
    lang = execute_query("SELECT lang FROM subjects WHERE id = %s", (id,), fetch_result=True)[0]["lang"]

    # Tüm konuları al
    subjects_query = execute_query("SELECT id, subject FROM subjects WHERE lang = %s", (lang,), fetch_result=True)
    subjects = [{"name": row['subject'], "id": row['id']} for row in subjects_query]

    # İlgili konuyu al
    subject_query = execute_query("SELECT * FROM subjects WHERE id = %s", (id,), fetch_result=True)[0]

    # Render edilecek veriyi hazırla
    data = {
        "lang": lang,
        "content1": subject_query["content1"],
        "subject": subject_query["subject"],
        "content2": subject_query["content2"],
        "code": subject_query["code"],
        "video": subject_query["video"]
    }

    # subject.html şablonunu kullanarak veriyi render et
    return render_template("subject.html", subjects=subjects, data=data, questions=questions)


app.run(port=80)