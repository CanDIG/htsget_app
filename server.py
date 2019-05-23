from flask import Flask
import connexion
import config

# Create the application instance
app = connexion.App(__name__, specification_dir='./')

app.add_api('swagger.yaml')

@app.route('/')
def index():
    return 'INDEX'

if __name__ == '__main__':
    app.run(port = config.port, debug=True)