FROM python:3
WORKDIR /usr/src/app
ADD wikiwhotest.py .
ADD WikiWho/utils.py .
ADD WikiWho/wikiwho.py .
ADD WikiWho/structures.py .
RUN pip install flask
RUN pip install flask_restful
RUN pip install requests
EXPOSE 3333
CMD [ "python", "./wikiwhotest.py"]