from pysam import VariantFile
from tempfile import NamedTemporaryFile

# ntf = NamedTemporaryFile(prefix='htsget', suffix='', dir='./write_files',
#                                       mode='wb', delete=False)

# print(ntf.name)

# vcf_in = VariantFile('./files/NA18537.vcf.gz')
# vcf_out = VariantFile(ntf.name, 'w', header=vcf_in.header)
# for rec in vcf_in.fetch(contig='21', start=27148269):
#     print(rec.pos)
    # vcf_out.write(rec)

# with open(ntf.name, 'rb') as f:
#     data = f.read(1000000)
    # print(data)

# def append_to(element, to=[]):
#     if to == []:
#         to = []
#     to.append(element)
#     return to

# my_list = append_to(12)
# print(my_list)

# my_other_list = append_to(42)
# print(my_other_list)

def get_variants(id, start, end):
    urls = []
    partition_amt = 2 # 10 million
    partitions = int( (end - start) / partition_amt )
    if( partitions >= 1 and start != None and end != None ):
        slice_start = start
        slice_end = 0
        for i in range(partitions):
            slice_end = slice_start + partition_amt
            create_slice(urls, id, slice_start, slice_end)
            slice_start = slice_end
        create_slice(urls, id, slice_start, end)
    print(urls)

def create_slice(arr, id, slice_start, slice_end):
    host = "0.0.0.0:8080"
    url = f"http://{host}/data?={id}&start={slice_start}&end={slice_end}"
    arr.append({
        'url': url, 
        'start': slice_start,
        'end': slice_end
    })
    slice_start = slice_end

# get_variants('HG02102', 2, 13)

test = {
  "htsget": {
    "format": "VCF",
    "urls": [
      {
        "url": "http://0.0.0.0:5000/data?id=HG02102&ref=21&start=17148269&end=27148269"
      },
      {
        "url": "http://0.0.0.0:5000/data?id=HG02102&ref=21&start=27148269&end=37148269"
      },
      {
        "url": "http://0.0.0.0:5000/data?id=HG02102&ref=21&start=37148269&end=42856478"
      }
    ]
  }
}

test1 = {u'urls': [u'http://0.0.0.0:5000/data?id=HG02102'], u'format': u'VCF'}

print(create_slice)
