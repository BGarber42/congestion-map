# 1. Use an official Python runtime as a parent image
FROM python:3.13-slim

# 2. Set the working directory in the container
WORKDIR /code

# 3. Copy the requirements file and install dependencies using pip
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 4. Copy the rest of the application code
COPY ./app /code/app
COPY run_worker.py .

# 5. Set the default command to run the API
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers"]
