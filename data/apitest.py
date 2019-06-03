import requests
from ast import literal_eval
from ga4gh.dos.client import Client
import datetime
import pytz

# id = "0dfd077c-d7c0-4ff3-97b4-5202bb9d9880"
# URL = f"http://0.0.0.0:8080/ga4gh/drs/v1/objects/{id}"

# r = requests.get(url = URL)
# data = r.json()
# print(data['object']['urls'][0]['url'])
# test = literal_eval('{"a": 1}')

d = datetime.datetime.utcnow()
d_with_timezone = d.replace(tzinfo=pytz.UTC)

client = Client("http://0.0.0.0:8080/ga4gh/dos/v1/")
c = client.client
models = client.models

DataObject = models.get_model('DataObject')
Checksum = models.get_model('Checksum')
URL = models.get_model('URL')

# NA18537_2 = DataObject()
# NA18537_2.id = 'NA18537'
# NA18537_2.name = 'NA18537.vcf.gz.tbi'
# NA18537_2.checksums = [
#     Checksum(checksum='eaf80af5e9e54db5936578bed06ffcdc', type='md5')]
# NA18537_2.urls = [
#     URL(
#         url="http://minio:9000/candig/reads/BroadHiSeqX_b37/NA12878",
#         system_metadata={'reference_name': 2, 'start': 1000, 'end': 20000})]
# NA18537_2.aliases = ['NA12878 chr 2 subset']
# NA18537_2.size = '555749'
# NA18537_2.created = d_with_timezone

# c.CreateDataObject(body={'data_object': NA18537_2}).result()

response = c.GetDataObject(data_object_id='NA18537').result()

print(response['data_object']["name"])
# print(response['data_object']["urls"][0]['url'])

# response = c.GetDataObject(data_object_id='na12878_5')
# try:
#     print(response.result())
# except:
#     print('hello')