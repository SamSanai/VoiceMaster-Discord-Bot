FROM python:3

WORKDIR /usr/src/app

RUN git clone https://github.com/zwthomas/VoiceMaster-Discord-Bot.git ./

RUN pip install discord.py

CMD ["python", "./openVoice.py"]
