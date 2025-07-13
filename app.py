from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import cv2
import face_recognition
import numpy as np
import os
import base64
from PIL import Image
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'face-unlock-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Directorio para caras conocidas
KNOWN_FACES_DIR = 'known_faces'
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

# Variables globales
known_face_encodings = []
known_face_names = []
camera = None

def load_known_faces():
    """Cargar caras conocidas desde el directorio"""
    global known_face_encodings, known_face_names
    known_face_encodings = []
    known_face_names = []
    
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.endswith(('.jpg', '.jpeg', '.png')):
            name = os.path.splitext(filename)[0]
            image_path = os.path.join(KNOWN_FACES_DIR, filename)
            
            # Cargar y codificar la imagen
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)
            
            if face_encodings:
                known_face_encodings.append(face_encodings[0])
                known_face_names.append(name)

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/register')
def register():
    """Página de registro de cara"""
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """Área protegida - solo accesible tras autenticación"""
    return render_template('dashboard.html')

@app.route('/api/register', methods=['POST'])
def register_face():
    """Registrar una nueva cara"""
    try:
        data = request.get_json()
        image_data = data['image']
        name = data['name']
        
        # Decodificar imagen base64
        image_data = image_data.split(',')[1]  # Remover "data:image/jpeg;base64,"
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convertir a formato OpenCV
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Detectar caras
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image)
        
        if not face_locations:
            return jsonify({'success': False, 'message': 'No se detectó ninguna cara'})
        
        # Guardar imagen
        filename = f"{name}.jpg"
        filepath = os.path.join(KNOWN_FACES_DIR, filename)
        cv2.imwrite(filepath, cv_image)
        
        # Recargar caras conocidas
        load_known_faces()
        
        return jsonify({'success': True, 'message': f'Cara de {name} registrada exitosamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@socketio.on('start_camera')
def handle_start_camera():
    """Iniciar cámara para autenticación"""
    global camera
    camera = cv2.VideoCapture(0)
    emit('camera_status', {'status': 'started'})

@socketio.on('stop_camera')
def handle_stop_camera():
    """Detener cámara"""
    global camera
    if camera:
        camera.release()
        camera = None
    emit('camera_status', {'status': 'stopped'})

@socketio.on('authenticate')
def handle_authenticate():
    """Procesar frame para autenticación"""
    global camera
    
    if not camera:
        emit('auth_result', {'success': False, 'message': 'Cámara no iniciada'})
        return
    
    # Capturar frame
    ret, frame = camera.read()
    if not ret:
        emit('auth_result', {'success': False, 'message': 'No se pudo capturar imagen'})
        return
    
    # Convertir a RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Detectar caras
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    # Enviar frame al cliente (opcional, para mostrar video)
    _, buffer = cv2.imencode('.jpg', frame)
    frame_base64 = base64.b64encode(buffer).decode('utf-8')
    emit('video_frame', {'frame': frame_base64})
    
    # Verificar si hay caras conocidas
    if not known_face_encodings:
        emit('auth_result', {'success': False, 'message': 'No hay caras registradas'})
        return
    
    # Comparar con caras conocidas
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        
        if any(matches):
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
                confidence = (1 - face_distances[best_match_index]) * 100
                
                emit('auth_result', {
                    'success': True, 
                    'message': f'¡Bienvenido {name}!',
                    'name': name,
                    'confidence': round(confidence, 2)
                })
                return
    
    # No se encontró coincidencia
    emit('auth_result', {'success': False, 'message': 'Cara no reconocida'})

if __name__ == '__main__':
    # Cargar caras conocidas al iniciar
    load_known_faces()
    
    print("🚀 Face Unlock System iniciado")
    print("📱 Accede a: http://localhost:5000")
    
    # Ejecutar aplicación
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)