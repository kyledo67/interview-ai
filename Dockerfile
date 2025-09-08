FROM python:3.11-slim
RUN apt-get update && apt-get install -y nodejs npm
WORKDIR /app
COPY ./backend /app/backend/
COPY ./frontend /app/frontend/
WORKDIR /app/frontend
RUN npm install && npm run build
WORKDIR /app/backend/
COPY ./backend/imports ./imports
RUN pip install --no-cache-dir -r imports
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


