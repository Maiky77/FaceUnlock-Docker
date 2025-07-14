# Usar Python 3.11 en Ubuntu
FROM python:3.11-slim

# Instalar dependencias básicas para OpenCV y face_recognition
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    python3-dev \
    python3-pip \
    libopencv-dev \
    python3-opencv \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libatlas-base-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements.txt primero (para cache de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear directorio para caras conocidas si no existe
RUN mkdir -p known_faces

# Exponer puerto 5000
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]