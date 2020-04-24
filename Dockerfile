FROM python:3

WORKDIR /usr/src/app

COPY . .

RUN pip install discord.py

CMD ["python", "./voicecreate.py"]
