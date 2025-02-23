# Usa una imagen oficial de Python
FROM python:3.10-slim

# Instala ffmpeg y cualquier otra librería si hace falta
RUN apt-get update && apt-get install -y ffmpeg

# Crea un directorio de trabajo para tu app
WORKDIR /app

# Copia el archivo de dependencias e instálalas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de tu código al contenedor
COPY . .

# Expón el puerto (no siempre obligatorio en Railway, pero es buena práctica)
EXPOSE 8000

# Comando para iniciar tu aplicación:
# - gunicorn sirve "app.py", donde la variable principal de Flask se llama "app"
# - Binding en 0.0.0.0:8000 (Luego Railway redirige 0.0.0.0:$PORT, nosotros usamos 8000)
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]