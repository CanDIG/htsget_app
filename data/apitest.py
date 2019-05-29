import requests
from ast import literal_eval
from ga4gh.dos.client import Client

# id = "0dfd077c-d7c0-4ff3-97b4-5202bb9d9880"
# URL = f"http://0.0.0.0:8080/ga4gh/drs/v1/objects/{id}"

# r = requests.get(url = URL)
# data = r.json()
# print(data['object']['urls'][0]['url'])
# test = literal_eval('{"a": 1}')
local_client = Client('http://localhost:8080/ga4gh/dos/v1')
client = local_client.client
models = local_client.models
ListDataObjectsRequest = models.get_model('ListDataObjectsRequest')
list_request = client.ListDataObjects(page_size=10000000)
list_response = list_request.result()
print("Number of Data Objects: {} ".format(len(list_response.data_objects)))