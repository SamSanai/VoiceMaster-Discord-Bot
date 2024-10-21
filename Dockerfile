FROM python:3.9 

# Install dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy source
COPY . .

# Run app
CMD ["python", "./voicecreate.py"] 
