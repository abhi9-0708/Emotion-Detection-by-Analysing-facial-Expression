
import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import re
import cv2
import numpy as np
from tensorflow.keras.models import load_model
import io
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from api import recommend_media, emotion_dict

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')

DATABASE = 'users.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL
                )''')
    conn.commit()
    conn.close()

init_db()

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')
ADMIN_PASSWORD_HASH = generate_password_hash(os.getenv('ADMIN_PASSWORD', 'adminpassword'))

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_password(password):
    return len(password) >= 8

# Load emotion detection model
model_path = "C:\\Users\\abhi9\\Desktop\\emotion_detection\\model.h5"
if os.path.exists(model_path):
    model = load_model(model_path, compile=False)
    print("Model loaded successfully.")
else:
    print(f"Error: Model file not found at {model_path}")
    exit()

# Emotion detection setup
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
img_size = 224
emotion_mapping = {0: 'sad', 1: 'fear', 2: 'surprise', 3: 'neutral', 4: 'disgust', 5: 'happy', 6: 'angry'}

def predict_emotion_from_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    detected_emotions = []
    for (x, y, w, h) in faces:
        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (img_size, img_size))
        rgb_face = np.stack((face,) * 3, axis=-1)  # Convert to RGB
        rgb_face = rgb_face / 255.0
        rgb_face = np.expand_dims(rgb_face, axis=0)  # Add batch dimension
        prediction = model.predict(rgb_face, verbose=0)
        emotion_idx = int(np.argmax(prediction))
        detected_emotions.append(emotion_idx)
        emotion_label = emotion_mapping[emotion_idx]
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
        cv2.putText(img, emotion_label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
    predicted_emotion = detected_emotions[0] if detected_emotions else None
    return img, predicted_emotion

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        if not validate_email(email):
            flash('Invalid email format.', 'danger')
            return redirect(url_for('signup'))
        if not validate_password(password):
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('signup'))
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                         (name, email, hashed_password))
            conn.commit()
            flash('Account created successfully. Please login.', 'success')
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'danger')
        finally:
            conn.close()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin'] = True
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('welcome'))
        else:
            flash('Incorrect email or password.', 'danger')
    return render_template('login.html')

@app.route('/welcome')
def welcome():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    session.pop('log_inserted', None)
    return render_template('welcome.html', username=session['user_name'])

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin'):
        flash('Unauthorized access. Admins only.', 'danger')
        return redirect(url_for('login'))
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        new_name = request.form['name']
        new_password = request.form.get('password')

        if new_password:
            hashed_password = generate_password_hash(new_password)
            conn.execute('UPDATE users SET name = ?, password = ? WHERE id = ?', 
                         (new_name, hashed_password, session['user_id']))
        else:
            conn.execute('UPDATE users SET name = ? WHERE id = ?', 
                         (new_name, session['user_id']))

        conn.commit()
        conn.close()
        session['user_name'] = new_name
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('welcome'))

    conn.close()
    return render_template('edit_profile.html', user=user)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        flash('No file part in request.', 'danger')
        return redirect(url_for('welcome'))
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('welcome'))
    if file:
        file_stream = file.read()
        npimg = np.frombuffer(file_stream, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if img is None:
            flash('Invalid image file.', 'danger')
            return redirect(url_for('welcome'))
        annotated_img, emotion_id = predict_emotion_from_image(img)
        session['predicted_emotion'] = emotion_id

        if not session.get('log_inserted'):
            conn = get_db_connection()
            user = conn.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            email = user['email'] if user else 'unknown'
            emotion_label = emotion_dict.get(emotion_id, 'Unknown Emotion')
            
            recommendations = recommend_media(emotion_id)
            music_playlist = recommendations.get('music', []) if recommendations else []
            podcast_playlist = recommendations.get('podcasts', []) if recommendations else []
            
            music_str = ", ".join(
                [f"{track.get('name', 'Unknown Title')} by {track.get('artist', 'Unknown Artist')}"
                 for track in music_playlist]
            ) if music_playlist else "No music"
            
            podcast_str = ", ".join(
                [f"{podcast.get('name', 'Unknown Podcast')} by {podcast.get('publisher', 'Unknown Publisher')}"
                 for podcast in podcast_playlist]
            ) if podcast_playlist else "No podcasts"
            
            playlist_str = f"Music: {music_str}; Podcasts: {podcast_str}"
            
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute('INSERT INTO logs (email, emotion, datetime, playlist) VALUES (?, ?, ?, ?)', 
                         (email, emotion_label, now_str, playlist_str))
            conn.commit()
            conn.close()
            session['log_inserted'] = True

        _, buffer = cv2.imencode('.jpg', annotated_img)
        io_buf = io.BytesIO(buffer)
        return Response(io_buf.getvalue(), mimetype='image/jpeg')

@app.route('/live_webcam', methods=['POST'])
def live_webcam():
    if 'frame' not in request.files:
        return Response("No frame data", status=400)
    
    frame_file = request.files['frame']
    frame_stream = frame_file.read()
    npimg = np.frombuffer(frame_stream, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    
    if frame is None:
        return Response("Invalid frame data", status=400)
    
    annotated_frame, emotion_id = predict_emotion_from_image(frame)
    
    if 'emotion_counts' not in session:
        session['emotion_counts'] = {str(k): 0 for k in range(7)}
    
    if emotion_id is not None:
        session['emotion_counts'][str(emotion_id)] += 1
        session.modified = True
    
    _, buffer = cv2.imencode('.jpg', annotated_frame)
    return Response(buffer.tobytes(), mimetype='image/jpeg')

@app.route('/recommend_media')
def recommend_media_route():
    emotion_id = session.get('predicted_emotion')
    if emotion_id is None:
        return jsonify({"error": "No emotion detected"}), 400
    recommendations = recommend_media(emotion_id)
    if not recommendations:
        return jsonify({"error": "No recommendations found"}), 500
    return jsonify(recommendations)

@app.route('/live_summary')
def live_summary():
    emotion_counts = session.get('emotion_counts')
    if not emotion_counts:
        return jsonify({"error": "No emotion data available."}), 400

    emotion_counts_int = {int(k): v for k, v in emotion_counts.items()}
    highest_emotion_index = max(emotion_counts_int, key=emotion_counts_int.get)
    highest_emotion_label = emotion_dict.get(highest_emotion_index, "Unknown")
    
    recommendations = recommend_media(highest_emotion_index)
    music_tracks = recommendations.get('music', []) if recommendations else []
    podcasts = recommendations.get('podcasts', []) if recommendations else []
    
    music_str = ", ".join(
        [f"{track.get('name', 'Unknown Title')} by {track.get('artist', 'Unknown Artist')}"
         for track in music_tracks]
    ) if music_tracks else "No music"
    
    podcast_str = ", ".join(
        [f"{podcast.get('name', 'Unknown Podcast')} by {podcast.get('publisher', 'Unknown Publisher')}"
         for podcast in podcasts]
    ) if podcasts else "No podcasts"
    
    playlist_str = f"Music: {music_str}; Podcasts: {podcast_str}"
    
    conn = get_db_connection()
    user = conn.execute('SELECT email FROM users WHERE id = ?', (session.get('user_id'),)).fetchone()
    email = user['email'] if user else 'unknown'
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        'INSERT INTO logs (email, emotion, datetime, playlist) VALUES (?, ?, ?, ?)',
        (email, highest_emotion_label, now_str, playlist_str)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        "emotion_counts": {emotion_dict[k]: v for k, v in emotion_counts_int.items()},
        "highest_emotion": highest_emotion_label,
        "music": music_tracks[:10],
        "podcasts": podcasts[:5]
    })

def init_feedback_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    feedback TEXT NOT NULL
                )''')
    conn.commit()
    conn.close()

init_feedback_db()

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'user_id' not in session:
        flash('Please log in to provide feedback.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        feedback_text = request.form.get('feedback')
        if not feedback_text:
            flash('Feedback cannot be empty.', 'danger')
            return redirect(url_for('feedback'))
        
        conn = get_db_connection()
        user = conn.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('login'))
        recipient_email = user['email']
        
        conn.execute('INSERT INTO feedback (email, feedback) VALUES (?, ?)', (recipient_email, feedback_text))
        conn.commit()
        conn.close()
        
        try:
            SENDER_EMAIL = os.environ.get('EMAIL_USER')
            SENDER_PASSWORD = os.environ.get('EMAIL_PASS')
            
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = recipient_email
            msg['Subject'] = "Feedback Received"
            msg.attach(MIMEText(f"Dear user,\n\nThank you for your feedback:\n\n{feedback_text}\n\nBest regards,\nYour Team", 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
            server.quit()
        except Exception as e:
            flash(f'Feedback submitted but failed to send email: {str(e)}', 'danger')
            return redirect(url_for('welcome'))
        
        flash('Feedback submitted successfully. An email has been sent to you!', 'success')
        return redirect(url_for('welcome'))
    
    return render_template('feedback.html')

def init_logs_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    emotion TEXT,
                    datetime TEXT,
                    playlist TEXT
                )''')
    conn.commit()
    conn.close()

init_logs_db()

@app.route('/logs')
def view_logs():
    if 'user_id' not in session:
        flash('Please log in to view logs.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM logs').fetchall()
    conn.close()
    
    return render_template('logs.html', logs=logs)
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin'] = True
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')
    return render_template('admin.html')
@app.route('/admin_feedback')
def admin_feedback():
    # Ensure only admin can access this route
    if not session.get('admin'):
        flash('Unauthorized access. Admins only.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    # Retrieve all feedback entries
    feedbacks = conn.execute('SELECT * FROM feedback ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('admin_feedback.html', feedbacks=feedbacks)

@app.route('/delete_user', methods=['GET'])
def delete_user():
    if not session.get('admin'):
        flash('Unauthorized access. Admins only.', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users WHERE email != ?", (ADMIN_EMAIL,)).fetchall()
    conn.close()
    return render_template('delete_user.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user_by_id(user_id):
    if not session.get('admin'):
        flash('Unauthorized access. Admins only.', 'danger')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User deleted successfully.", "success")
    return redirect(url_for('delete_user'))

if __name__ == '__main__':
    app.run(debug=True)