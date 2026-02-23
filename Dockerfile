# # 1. Use Python 3.11 Slim
# FROM python:3.11-slim

# # 2. Set working directory
# WORKDIR /app

# # 3. Install system dependencies (Required for Postgres/AI libs)
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libpq-dev \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# # 4. Copy requirements and install
# COPY requirements.txt .

# # CRITICAL: Remove Windows-only package and install the rest
# RUN sed -i '/pywin32/d' requirements.txt && \
#     pip install --no-cache-dir -r requirements.txt

# # 5. Install Gunicorn (Production Server)
# RUN pip install gunicorn whitenoise

# # 6. Copy your application code
# COPY . .

# # 7. Collect Static Files (CSS/JS)
# # This uses the STATIC_ROOT you just added
# RUN python manage.py collectstatic --noinput

# # 8. Create a non-root user (Security requirement for HF)
# RUN useradd -m -u 1000 user
# USER user
# ENV HOME=/home/user \
#     PATH=/home/user/.local/bin:$PATH

# # 9. Run the app on port 7860
# CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "120"]

# 1. Use Python 3.11 Slim
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy requirements and install
COPY requirements.txt .
RUN sed -i '/pywin32/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# 5. Install Gunicorn and WhiteNoise
RUN pip install gunicorn whitenoise

# 6. Copy your application code
COPY . .

# 7. Collect Static Files
RUN python manage.py collectstatic --noinput

# 8. Create a non-root user for Hugging Face
RUN useradd -m -u 1000 user
# Ensure the user has permissions to the app directory (needed for migrations/sqlite)
RUN chown -R user:user /app 
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# 9. Run Migrations, Create Superuser, and Start Gunicorn
# This shell command checks if a superuser exists before trying to create one
CMD python manage.py migrate && \
    echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.filter(username='admin').exists() or \
User.objects.create_superuser('admin', 'admin@ubtiinc.com', 'admin')" | python manage.py shell && \
    gunicorn config.wsgi:application --bind 0.0.0.0:7860 --workers 2 --timeout 120