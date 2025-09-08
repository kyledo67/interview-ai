FROM python:3.11-slim
WORKDIR /app
COPY ./backend /app/backend/
COPY ./frontend /app/frontend/
WORKDIR /app/backend/
COPY ./backend/imports ./imports
RUN pip install --no-cache-dir -r imports
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


