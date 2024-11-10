from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from PIL import Image
import os
import json
import uuid

from pydub import AudioSegment

app = Flask(__name__)
app.secret_key = 'secret_key'

# Configuración de rutas de archivos y carpetas
USERS_FILE = 'users.json'
POSTS_FILE = 'posts.json'
EDIT_PASSWORD = "Luciana1Luciana2"
UPLOAD_FOLDER = 'static/images/profiles'
POSTS_FOLDER = 'static/images/posts'
QUOTAS_FILE = 'quotas.json'
CAMERAS_FILE = 'cameras.json'

# Crear carpetas necesarias si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(POSTS_FOLDER, exist_ok=True)

# ------------------ Funciones Auxiliares ------------------ #






# Función para cargar datos desde un archivo JSON
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    else:
        return {}

# Función para guardar datos en un archivo JSON
def save_data(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return []

def save_json(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


def load_quotas():
    return load_json(QUOTAS_FILE)

def save_quotas(quotas):
    save_json(quotas, QUOTAS_FILE)

def load_expenses():
    with open("expenses.json", "r") as file:
        return json.load(file)
    

# Function to get total expenses for the selected month
def get_total_expenses(month, year):
    expenses = load_expenses()
    month_key = f"{year}-{month:02d}"
    month_expenses = expenses.get(month_key, [])
    total_expenses = sum(expense['amount'] for expense in month_expenses)
    return total_expenses

# Function to get the total collected amount from the previous month
def get_previous_month_balance(month, year):
    if month == 1:
        previous_month, previous_year = 12, year - 1
    else:
        previous_month, previous_year = month - 1, year
    previous_month_key = f"{previous_year}-{previous_month:02d}"
    quotas = load_quotas()
    previous_month_data = quotas.get(previous_month_key, {})
    return previous_month_data.get("total_collected", 0)

def get_sundays_of_month(year, month):
    sundays = []
    start_date = datetime(year, month, 1)
    while start_date.weekday() != 6:
        start_date += timedelta(days=1)
    while start_date.month == month:
        sundays.append(start_date)
        start_date += timedelta(days=7)
    return sundays

# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename, allowed_extensions={'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'ogg', 'amr'}):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


# ------------------ Rutas de Autenticación ------------------ #
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_json(USERS_FILE)

        if username in users and check_password_hash(users[username]['password'], password):
            session['username'] = username
            return redirect(url_for('view'))
        else:
            flash("Nombre de usuario o contraseña incorrectos")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        profile_picture = request.files['profile_picture']
        
        users = load_json(USERS_FILE)
        
        if username in users:
            flash("El nombre de usuario ya existe")
            return redirect(url_for('register'))
        
        profile_path = None
        if profile_picture and allowed_file(profile_picture.filename):
            profile_filename = f"{username}_profile.jpg"
            profile_path = f"images/profiles/{profile_filename}"
            profile_picture.save(f"static/{profile_path}")
        else:
            profile_path = 'images/profiles/default_profile.jpg'

        users[username] = {
            'password': generate_password_hash(password),
            'profile_picture': profile_path
        }
        save_json(users, USERS_FILE)
        
        flash("Registro exitoso")
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('authorized_edit', None)
    return redirect(url_for('login'))

# ------------------ Rutas de Vista y Publicaciones ------------------ #
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('view'))
    return redirect(url_for('login'))

@app.route('/view')
def view():
    if 'username' not in session:
        return redirect(url_for('login'))

    users = load_json(USERS_FILE)
    username = session['username']
    user = users.get(username, {})
    profile_picture = user.get('profile_picture', 'images/profiles/default_profile.jpg')

    # Obtener mes y año de la URL, o usar el mes y año actual
    selected_month = int(request.args.get('month', datetime.now().month))
    selected_year = int(request.args.get('year', datetime.now().year))
    month_key = f"{selected_year}-{selected_month:02d}"

    # Cargar datos de cuotas, report y expenses
    quotas = load_json('quotas.json')
    report = load_json('report.json')
    
    contributions = quotas.get(month_key, {})
    report_data = report.get(month_key, {
        "individual_reports": {},
        "total_collected": 0,
        "total_expenses": 0,
        "saldo_real": 0,
        "previous_balance": 0,
        "total_balance": 0
    })

    sundays_of_selected_month = get_sundays_of_month(selected_year, selected_month)
    members = sorted(contributions.keys()) if contributions else []
    month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    selected_month_name = month_names[selected_month - 1]

    # Renderizar la plantilla con todos los datos necesarios
    return render_template(
        'view.html',
        user=user,
        profile_picture=profile_picture,
        posts=sorted(load_json(POSTS_FILE), key=lambda x: x['date'], reverse=True),
        members=members,
        contributions=contributions,
        selected_month=selected_month,
        selected_year=selected_year,
        sundays_of_selected_month=sundays_of_selected_month,
        month_names=month_names,
        selected_month_name=selected_month_name,
        report_data=report_data
    )

# Ruta para agregar una publicación con imagen, video y audio
@app.route('/add_post', methods=['POST'])
def add_post():
    if 'username' not in session:
        return redirect(url_for('login'))

    content = request.form['content']
    image = request.files.get('image')
    video = request.files.get('video')
    audio = request.files.get('audio')

    media_paths = {'image': None, 'video': None, 'audio': None}
    timestamp = datetime.now().timestamp()

    # Procesar imagen
    if image and allowed_file(image.filename, {'png', 'jpg', 'jpeg', 'gif'}):
        image_filename = f"{session['username']}_{timestamp}_image.jpg"
        image_path = os.path.join(POSTS_FOLDER, image_filename)
        try:
            img = Image.open(image)
            img = img.convert("RGB")
            img.save(image_path, "JPEG")
            media_paths['image'] = f"images/posts/{image_filename}"
        except Exception as e:
            print("Error al procesar la imagen:", e)
            flash("Error al cargar la imagen")

    # Procesar video
    if video and allowed_file(video.filename, {'mp4', 'avi', 'mov'}):
        video_filename = f"{session['username']}_{timestamp}_video.mp4"
        video_path = os.path.join(POSTS_FOLDER, video_filename)
        video.save(video_path)  # Guardar directamente sin procesamiento
        media_paths['video'] = f"images/posts/{video_filename}"
        print(f"Video guardado en: {video_path}")
    else:
        print("El archivo de video no es válido o no se pudo guardar.")

    # Procesar audio
    if audio and allowed_file(audio.filename, {'mp3', 'wav', 'ogg', 'amr'}):
        audio_filename = f"{session['username']}_{timestamp}_audio.mp3"  # Guardaremos como .mp3
        audio_path = os.path.join(POSTS_FOLDER, audio_filename)
        try:
            # Detectar si el archivo es .amr o cualquier otro formato no estándar
            if audio.filename.rsplit('.', 1)[1].lower() == 'amr':
                audio_clip = AudioSegment.from_file(audio, format="amr")
            else:
                audio_clip = AudioSegment.from_file(audio)

            # Exportar a mp3 para compatibilidad
            audio_clip.export(audio_path, format="mp3")
            media_paths['audio'] = f"images/posts/{audio_filename}"
            print(f"Audio guardado en: {audio_path}")

        except Exception as e:
            print("Error al procesar el audio:", e)
            flash("Error al cargar el audio")

    # Crear la nueva publicación con un ID único
    new_post = {
        "id": str(uuid.uuid4()),  # Generar un UUID único para la publicación
        "username": session['username'],
        "content": content,
        "image": media_paths['image'],
        "video": media_paths['video'],
        "audio": media_paths['audio'],
        "date": datetime.now().isoformat(),
        "likes": 0,
        "hearts": 0,
        "comments": []
    }

    # Guardar la publicación en el archivo JSON
    posts = load_json(POSTS_FILE)
    posts.append(new_post)
    save_json(posts, POSTS_FILE)

    return redirect(url_for('view'))


@app.route('/edit', methods=['GET', 'POST'])
def edit():
    if 'username' not in session:
        flash("Debes iniciar sesión para acceder a esta página.")
        return redirect(url_for('login'))

    # Obtener el mes y el año seleccionados de la URL o usa el mes actual por defecto
    selected_month = int(request.args.get('month', datetime.now().month))
    selected_year = int(request.args.get('year', datetime.now().year))
    month_key = f"{selected_year}-{selected_month:02d}"

    # Cargar datos de quotas, report y expenses
    quotas = load_json('quotas.json')
    report = load_json('report.json')
    expenses = load_json('expenses.json')

    # Obtener los datos de gastos del mes seleccionado
    total_gastos = sum(item['amount'] for item in expenses.get(month_key, []))

    # Asegurar que el mes esté inicializado en report
    if month_key not in report:
        report[month_key] = {
            "individual_reports": {},
            "total_collected": 0,
            "total_debt": 0,
            "total_expenses": total_gastos,
            "saldo_real": 0,
            "previous_balance": 0,
            "total_balance": 0
        }

    # Definir report_data para usar en la plantilla
    report_data = report[month_key]
    report_data["total_expenses"] = total_gastos  # Agregar gastos al reporte
    report_data["saldo_real"] = report_data["total_collected"] - total_gastos  # Calcular el saldo real

    # Calcular la recaudación del mes anterior si existe
    previous_month_key = f"{selected_year}-{selected_month - 1:02d}"
    if previous_month_key in report:
        report_data["previous_balance"] = report[previous_month_key]["total_balance"]
    else:
        report_data["previous_balance"] = 0

    # Calcular la recaudación real como la suma de saldo_real y previous_balance
    report_data["total_balance"] = report_data["saldo_real"] + report_data["previous_balance"]

    # Cargar datos de contribuciones y miembros
    contributions = quotas.get(month_key, {})
    sundays_of_selected_month = get_sundays_of_month(selected_year, selected_month)
    members = sorted(contributions.keys()) if contributions else []

    # Nombres de los meses
    month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    selected_month_name = month_names[selected_month - 1]

    # Guardar el reporte actualizado
    save_json(report, 'report.json')

    # Renderizar la plantilla
    return render_template(
        'edit.html',
        members=members,
        contributions=contributions,
        selected_month=selected_month,
        selected_year=selected_year,
        sundays_of_selected_month=sundays_of_selected_month,
        month_names=month_names,
        selected_month_name=selected_month_name,
        report_data=report_data  # Pasar report_data a la plantilla
    )


@app.route('/save_contributions', methods=['POST'])
def save_contributions():
    selected_month = request.form.get('selected_month')
    selected_year = request.form.get('selected_year')
    month_key = f"{selected_year}-{selected_month}"

    quotas = load_json('quotas.json')
    report = load_json('report.json')  # Cargar el reporte de aportes
    expenses = load_json('expenses.json')  # Cargar los gastos

    if month_key not in quotas:
        quotas[month_key] = {}

    contributions = quotas[month_key]
    quota_amount = int(request.form.get('quota_amount', 20))

    for key, value in request.form.items():
        if key.startswith("contribution_status["):
            member = key.split("[")[1].split("]")[0]
            date = key.split("[")[2].split("]")[0]

            if member not in contributions:
                contributions[member] = {}
            contributions[member][date] = value

    # Procesamiento de contribuciones individuales
    report[month_key] = {"individual_reports": {}, "total_collected": 0, "total_debt": 0, "previous_balance": 0}
    month_report = report[month_key]

    for member, dates in contributions.items():
        member_report = {"contributed": 0, "debt": 0, "debt_dates": [], "exonerated_dates": []}
        for date, status in dates.items():
            if status == "check":
                member_report["contributed"] += quota_amount
            elif status == "x-red":
                member_report["debt"] += quota_amount
                member_report["debt_dates"].append(date)
            elif status == "o-blue":
                member_report["exonerated_dates"].append(date)

        if member_report["debt"] > 0:
            member_report["status"] = "En deuda"
        elif member_report["contributed"] > 0:
            member_report["status"] = "Al día"
        elif member_report["exonerated_dates"]:
            member_report["status"] = "Exonerado"
        else:
            member_report["status"] = "Sin contribuciones"

        month_report["individual_reports"][member] = member_report

    # Calcular totales del mes
    month_report["total_collected"] = sum(
        report["contributed"] for report in month_report["individual_reports"].values()
    )
    month_report["total_debt"] = sum(
        report["debt"] for report in month_report["individual_reports"].values()
    )

    # Calcular el saldo anterior si existe
    previous_month_key = f"{selected_year}-{int(selected_month) - 1:02d}"
    if previous_month_key in report:
        month_report["previous_balance"] = report[previous_month_key]["total_collected"] - report[previous_month_key]["total_debt"]

    # Suma del saldo anterior y actual
    month_report["total_balance"] = month_report["previous_balance"] + month_report["total_collected"] - month_report["total_debt"]

    # **Calcular Total de Gastos del Mes**
    total_expenses = 0
    if month_key in expenses:
        # Sumamos los montos de todos los gastos en el mes
        total_expenses = sum(item["amount"] for item in expenses[month_key])

    # Almacenar el total de gastos en el reporte
    month_report["total_expenses"] = total_expenses
    month_report["saldo_real"] = month_report["total_balance"] - total_expenses

    # Guardar los cambios en los archivos JSON
    save_json(quotas, 'quotas.json')
    save_json(report, 'report.json')

    flash("Cambios guardados con éxito")
    return redirect(url_for('edit', month=selected_month))


# Ruta de edición de gastos, solo accesible si tiene permisos
@app.route('/edit_gastos', methods=['GET', 'POST'])
def edit_gastos():
    if not session.get('authorized_edit'):
        flash("Acceso denegado. Solicita permisos para editar.")
        return redirect(url_for('request_edit_access'))
    
    selected_month = int(request.args.get('month', datetime.now().month))
    selected_year = int(request.args.get('year', datetime.now().year))
    month_key = f"{selected_year}-{selected_month:02d}"

    # Cargar datos de gastos
    expenses = load_data('expenses.json')
    month_expenses = expenses.get(month_key, [])

    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        reason = request.form.get('reason')
        date = f"{selected_year}-{selected_month:02d}-{datetime.now().day:02d}"

        if month_key not in expenses:
            expenses[month_key] = []
        
        expenses[month_key].append({"amount": amount, "reason": reason, "date": date})
        save_data('expenses.json', expenses)
        flash("Gasto agregado exitosamente.")
        return redirect(url_for('edit_gastos', month=selected_month, year=selected_year))

    return render_template('edit_gastos.html', month=selected_month, year=selected_year, month_expenses=month_expenses)


# Ruta de visualización de gastos, sin permisos especiales
@app.route('/view_gastos', methods=['GET'])
def view_gastos():
    selected_month = int(request.args.get('month', datetime.now().month))
    selected_year = int(request.args.get('year', datetime.now().year))
    month_key = f"{selected_year}-{selected_month:02d}"

    # Cargar datos de gastos
    expenses = load_data('expenses.json')
    month_expenses = expenses.get(month_key, [])

    return render_template('view_gastos.html', month=selected_month, year=selected_year, month_expenses=month_expenses)


# Ruta de solicitud de acceso de edición
@app.route('/request_edit_access', methods=['GET', 'POST'])
def request_edit_access():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == EDIT_PASSWORD:
            session['authorized_edit'] = True
            flash("Acceso concedido para edición.")
            return redirect(url_for('edit'))
        else:
            flash("Contraseña incorrecta.")
    return render_template('request_edit_access.html')


@app.route('/add_member', methods=['POST'])
def add_member():
    if 'username' not in session or not session.get('authorized_edit'):
        flash("No tienes permiso para agregar miembros.")
        return redirect(url_for('edit'))

    new_member = request.form.get('new_member')
    selected_month = request.form.get('selected_month')
    selected_year = request.form.get('selected_year')

    if not new_member or not selected_month or not selected_year:
        flash("Error: Datos incompletos para agregar el miembro.")
        return redirect(url_for('edit'))

    # Formatear el mes y año seleccionado en el formato adecuado para la clave de quotas
    month_key = f"{selected_year}-{selected_month.zfill(2)}"
    quotas = load_quotas()

    # Agregar el nuevo miembro al mes seleccionado
    if month_key not in quotas:
        quotas[month_key] = {}

    # Crear las fechas de los domingos del mes
    sundays = get_sundays_of_month(int(selected_year), int(selected_month))
    quotas[month_key][new_member] = {sunday.strftime('%Y-%m-%d'): "blank" for sunday in sundays}

    # Guardar las cuotas actualizadas
    save_quotas(quotas)
    flash(f"Integrante {new_member} añadido para el mes {selected_month}.")
    return redirect(url_for('edit', month=selected_month))



@app.route('/delete_member', methods=['POST'])
def delete_member():
    # Convertir los valores de mes y año a enteros
    selected_month = int(request.form.get('selected_month'))
    selected_year = int(request.form.get('selected_year'))
    member_to_delete = request.form.get('member')
    month_key = f"{selected_year}-{selected_month:02d}"

    # Cargar los datos de quotas
    quotas = load_json('quotas.json')

    # Verificar que el miembro exista en el mes específico y eliminarlo
    if month_key in quotas and member_to_delete in quotas[month_key]:
        del quotas[month_key][member_to_delete]
        save_json(quotas, 'quotas.json')
        flash(f"{member_to_delete} ha sido eliminado con éxito.")
    else:
        flash("No se pudo eliminar al integrante.")

    # Redirigir a la página de edición con los parámetros de mes y año
    return redirect(url_for('edit', month=selected_month, year=selected_year))



# ------------------ Ruta de Edición de Perfil ------------------ #
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        flash("Debes iniciar sesión para acceder a esta página.")
        return redirect(url_for('login'))

    users = load_json(USERS_FILE)
    username = session['username']
    user_data = users.get(username, {})

    if request.method == 'POST':
        new_name = request.form.get('new_name')
        new_profile_picture = request.files.get('new_profile_picture')

        if new_name:
            user_data['name'] = new_name

        if new_profile_picture and allowed_file(new_profile_picture.filename):
            profile_filename = f"{username}_profile.jpg"
            profile_path = os.path.join(UPLOAD_FOLDER, profile_filename)
            new_profile_picture.save(profile_path)
            user_data['profile_picture'] = f"images/profiles/{profile_filename}"

        users[username] = user_data
        save_json(users, USERS_FILE)
        flash("Perfil actualizado con éxito.")
        return redirect(url_for('view'))

    return render_template('edit_profile.html', user_data=user_data)


@app.route('/control_camera')
def control_camera():
    cameras = load_cameras()  # Suponiendo que esta función carga las cámaras conectadas
    return render_template('control_camera.html', cameras=cameras)

def load_cameras():
    # Aquí podrías cargar las URLs de las cámaras desde una base de datos o un archivo JSON
    # Retornamos un diccionario con las URLs de las cámaras para mostrarlas en la plantilla
    cameras = [
        {"url": "http://camera1.local/stream", "name": "Cámara 1"},
        {"url": "http://camera2.local/stream", "name": "Cámara 2"}
    ]
    return cameras
@app.route('/connect_camera', methods=['POST'])
def connect_camera():
    camera_url = request.form.get('camera_url')
    if camera_url:
        add_camera(camera_url)  # Define `add_camera` para almacenar la nueva cámara
    return redirect(url_for('control_camera'))
def add_camera(camera_url):
    # Aquí almacenamos la URL de la cámara en un archivo JSON o base de datos
    cameras = load_cameras()
    cameras.append({"url": camera_url, "name": f"Cámara {len(cameras) + 1}"})
    # Guarda el nuevo estado en un archivo
    with open('cameras.json', 'w') as f:
        json.dump(cameras, f)
@app.route('/control', methods=['POST'])
def control():
    command = request.json.get('command')
    # Envía el comando al ESP32 o controlador del drone
    send_to_esp32(command)
    return jsonify({"status": "success", "command": command})
def send_to_esp32(command):
    # Aquí enviarías el comando al ESP32, por ejemplo, mediante una solicitud HTTP o un mensaje MQTT
    print(f"Enviando comando al ESP32: {command}")
@app.route('/pair_drone', methods=['POST'])
def pair_drone():
    # Aquí deberías implementar la lógica para emparejar con el ESP32 (IoT del drone)
    # Simulación: Suponemos que se conecta exitosamente
    # En la realidad, podrías hacer una solicitud HTTP al ESP32 y verificar el estado
    connected = True  # Cambiar a la lógica real de emparejamiento

    if connected:
        return jsonify({"status": "connected"})
    else:
        return jsonify({"status": "disconnected"})


# Ruta para dar Me gusta o Corazón a una publicación
@app.route('/like_post/<post_id>', methods=['POST'])
def like_post(post_id):
    data = request.get_json()
    reaction_type = data.get('reactionType')
    points = data.get('points', 1)

    posts = load_json(POSTS_FILE)  # Cargar publicaciones desde el JSON
    post = next((p for p in posts if str(p.get("id")) == post_id), None)

    if post:
        # Actualizar el número de likes o hearts en la publicación correspondiente
        if reaction_type == 'like':
            post["likes"] += points
        elif reaction_type == 'heart':
            post["hearts"] += points
        
        # Guardar cambios en el archivo JSON para hacerlos persistentes
        save_json(posts, POSTS_FILE)
        
        # Enviar los nuevos valores de likes y hearts al cliente
        return jsonify({"status": "success", "likes": post["likes"], "hearts": post["hearts"]})
    
    return jsonify({"status": "error", "message": "Post not found"})



@app.route('/add_comment', methods=['POST'])
def add_comment():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Obtener datos del formulario
    post_id = request.form.get('post_id')  # Obtener el ID de la publicación
    comment_text = request.form.get('comment_text')
    comment_audio = request.files.get('comment_audio')
    audio_path = None

    # Procesar archivo de audio si existe
    if comment_audio and allowed_file(comment_audio.filename, {'mp3', 'wav', 'ogg', 'amr'}):
        timestamp = datetime.now().timestamp()
        audio_filename = f"{session['username']}_{timestamp}_comment.mp3"
        audio_path = os.path.join(POSTS_FOLDER, audio_filename)
        audio = AudioSegment.from_file(comment_audio)
        audio.export(audio_path, format="mp3")
        audio_path = f"images/posts/{audio_filename}"

    # Cargar las publicaciones y buscar la específica usando el post_id
    posts = load_json(POSTS_FILE)
    new_comment = {
        "username": session['username'],
        "text": comment_text,
        "audio": audio_path,
        "date": datetime.now().isoformat()
    }

    # Buscar la publicación con el ID correspondiente y agregar el comentario
    for post in posts:
        if str(post.get("id")) == post_id:
            post['comments'].append(new_comment)  # Agregar comentario a la publicación encontrada
            save_json(posts, POSTS_FILE)
            break
    else:
        print("Error: Publicación no encontrada para agregar comentario")

    return redirect(url_for('view'))

def synchronize_likes_hearts(posts_from_screen):
    """
    Sincroniza los valores de likes y hearts del JSON con los valores en pantalla.
    Args:
        posts_from_screen (list): Lista de publicaciones desde la pantalla con 'id', 'likes', y 'hearts'.
    """
    posts = load_json(POSTS_FILE)  # Cargar publicaciones desde el JSON

    for screen_post in posts_from_screen:
        # Buscar la publicación correspondiente en el archivo JSON por ID
        post = next((p for p in posts if p["id"] == screen_post["id"]), None)
        if post:
            # Comparar y actualizar si los valores en pantalla son mayores
            if screen_post["likes"] > post["likes"]:
                post["likes"] = screen_post["likes"]
            if screen_post["hearts"] > post["hearts"]:
                post["hearts"] = screen_post["hearts"]

    # Guardar los cambios en el archivo JSON
    save_json(posts, POSTS_FILE)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
