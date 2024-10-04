FROM python:3.12-slim-bookworm

# Install necessary packages for MySQL and Python
RUN apt-get update \
    && apt-get install -y --no-install-recommends --no-install-suggests \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    python3-dev \
    && pip install --no-cache-dir --upgrade pip

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY ./requirements.txt /app
RUN pip install --no-cache-dir --requirement /app/requirements.txt

# Copy the rest of the application code
COPY . /app

# Expose the application port (for one replica)
EXPOSE 5000

# Command to run the Flask app
CMD ["sh", "-c", "python3 db_init.py && python3 app.py"]