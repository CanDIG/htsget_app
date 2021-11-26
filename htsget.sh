#!/usr/bin/env bash 
set -xe # To print debug message 

# Check python version
if ! [[ $(python3 --version | awk '{print $2}') =~ 3.6.* ]]; then 
     echo "Need python 3.6 to run the script"
     exit 1
fi

#Installing libraries 
python3 setup.py install
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements_dev.txt

# Running Scripts
python3 htsget_server/server.py &
sleep 5
pytest tests/test_htsget_server.py




