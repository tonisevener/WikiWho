FROM python:3
WORKDIR /usr/src/app
ADD router.py .
ADD utils.py .
ADD wikiwho.py .
ADD structures.py .
ADD whoColorUtils.py .
ADD whoColorHandler.py .
ADD whoColorParser.py .
ADD whoColorSpecial_markups.py .
RUN pip install flask
RUN pip install flask_restful
RUN pip install requests
RUN pip install python-dateutil
EXPOSE 3333
CMD [ "python", "./router.py"]