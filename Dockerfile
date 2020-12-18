FROM python:3
WORKDIR /usr/src/app
ADD wikiwhotest.py .
ADD WikiWho/utils.py .
ADD WikiWho/wikiwho.py .
ADD WikiWho/structures.py .
ADD WhoColor/whoColorUtils.py .
ADD WhoColor/whoColorHandler.py .
ADD WhoColor/whoColorParser.py .
ADD WhoColor/whoColorSpecial_markups.py .
RUN pip install flask
RUN pip install flask_restful
RUN pip install requests
RUN pip install python-dateutil
EXPOSE 3333
CMD [ "python", "./wikiwhotest.py"]