from pysam import VariantFile, AlignmentFile
from tempfile import NamedTemporaryFile

ntf = NamedTemporaryFile(prefix='htsget', suffix='', dir='./write_files',
                                      mode='wb', delete=False)

print(ntf.name)

vcf_in = VariantFile('./files/NA18537.vcf.gz')
vcf_out = VariantFile(ntf.name, 'w', header=vcf_in.header)

bam_in = AlignmentFile("./files/NA02102.bam", "rb")
for x in bam_in.fetch("chr4", 10144, 10200):
  print(x)

# print(test)
