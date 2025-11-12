#!/bin/bash
# Script de instalación para Raspberry Pi 4 - CCTV Logger

echo "=== Instalación de CCTV Logger en Raspberry Pi 4 ==="

# Actualizar sistema
echo "Actualizando sistema..."
sudo apt update && sudo apt upgrade -y

# Instalar dependencias del sistema
echo "Instalando dependencias del sistema..."
sudo apt install -y python3-pip python3-dev libatlas-base-dev libjpeg-dev libtiff-dev libpng-dev
sudo apt install -y libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev
sudo apt install -y libgtk-3-dev libcanberra-gtk3-module libcanberra-gtk-module

# Instalar OpenCV optimizado para Raspberry Pi
echo "Instalando OpenCV..."
pip3 install "opencv-python-headless>=4.8.0"

# Instalar TensorFlow Lite (requerido por MediaPipe)
echo "Instalando TensorFlow Lite..."
pip3 install tflite-runtime

# Instalar MediaPipe
echo "Instalando MediaPipe..."
pip3 install "mediapipe>=0.10.0"

# Instalar otras dependencias
echo "Instalando dependencias Python..."
pip3 install "requests>=2.28.0" "numpy>=1.21.0"

# Verificar instalación
echo "Verificando instalación..."
python3 -c "import cv2; print('OpenCV:', cv2.__version__)"
python3 -c "import mediapipe as mp; print('MediaPipe:', mp.__version__)"
python3 -c "import requests; print('Requests: OK')"

echo "=== Instalación completada ==="
echo "Para ejecutar: python3 main.py"
echo "Asegúrate de configurar credentials.json con tus tokens de Discord/Telegram"