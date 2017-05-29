#!/bin/bash

cd Flansible
source $HOME/anaconda/bin/activate py27
/usr/bin/screen -dmS Celery celery worker -A flansible.celery --loglevel=info
/usr/bin/screen -dmS Flansible python runserver.py
/usr/bin/screen -dmS Flower flower --broker=redis://localhost:6379/0

