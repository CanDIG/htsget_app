from flask import Flask
import connexion

# Create the application instance
app = connexion.App(__name__, specification_dir='./')

app.add_api('swagger.yaml')

@app.route('/')
def index():
    return 'INDEX'

if __name__ == '__main__':
    app.run(port = 5000, debug=True)