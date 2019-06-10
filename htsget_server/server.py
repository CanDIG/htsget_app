from flask import Flask
import connexion
import configparser

config = configparser.ConfigParser()
config.read('./config.ini')

# Create the application instance
app = connexion.App(__name__, specification_dir='./')

app.add_api('swagger.yaml')

@app.route('/')
def index():
    return 'INDEX'

if __name__ == '__main__':
    app.run(port = config['DEFAULT']['Port'], debug=True)