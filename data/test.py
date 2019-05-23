# def get_variants(id, start, end):
#     urls = []
#     partition_amt = 2 # 10 million
#     partitions = int( (end - start) / partition_amt )
#     if( partitions >= 1 and start != None and end != None ):
#         slice_start = start
#         slice_end = 0
#         for i in range(partitions):
#             slice_end = slice_start + partition_amt
#             create_slice(urls, id, slice_start, slice_end)
#             slice_start = slice_end
#         create_slice(urls, id, slice_start, end)
#     print(urls)

# def create_slice(arr, id, slice_start, slice_end):
#     host = "0.0.0.0:8080"
#     url = f"http://{host}/data?={id}&start={slice_start}&end={slice_end}"
#     arr.append({
#         'url': url, 
#         'start': slice_start,
#         'end': slice_end
#     })
#     slice_start = slice_end

# get_variants('HG02102', 2, 13)
file_types = ["Variant", "Read"]
file = "Variant"
print(file in file_types)