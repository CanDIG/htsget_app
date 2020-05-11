import os

from flask import Flask
import connexion
import configparser

config = configparser.ConfigParser()
config.read('./config.ini')

HTSGET_APP_PORT = os.getenv('HTSGET_APP_PORT')

# Create the application instance
app = connexion.App(__name__, specification_dir='./')

app.add_api('swagger.yaml')

@app.route('/')
def index():
    return 'INDEX'

if __name__ == '__main__':
    port = HTSGET_APP_PORT if HTSGET_APP_PORT else config['DEFAULT']['Port']
    app.run(port=port, debug=True)
