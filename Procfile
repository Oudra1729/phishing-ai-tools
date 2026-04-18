# Render / Railway / Heroku-style process file (project root = working directory)
web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 src.api:app
