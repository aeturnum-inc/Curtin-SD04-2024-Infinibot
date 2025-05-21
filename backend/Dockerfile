FROM python:3.9 AS development

WORKDIR /code

# Copy requirements first for better caching
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy application code
COPY ./app /code/app

# Production stage
FROM python:3.9-slim AS production

WORKDIR /code

# Copy only the necessary files from the builder stage
COPY --from=development /code/requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application code
COPY --from=development /code/app ./app

# Run with production settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]