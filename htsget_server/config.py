import configparser

config = configparser.ConfigParser()
config.read('./config.ini')

AUTHZ = config['authz']

TESTING = False
if config['DEFAULT']['Testing'] == "True":
    TESTING = True