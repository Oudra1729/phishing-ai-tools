# Render / Railway / Heroku — requires frontend/dist (run ./build.sh or use Dockerfile before deploy).
web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 src.api:app
