from pysam import VariantFile
from tempfile import NamedTemporaryFile

ntf = NamedTemporaryFile(prefix='htsget', suffix='', dir='./write_files',
                                      mode='wb', delete=False)

print(ntf.name)

vcf_in = VariantFile('./files/NA18537.vcf.gz')
vcf_out = VariantFile(ntf.name, 'w', header=vcf_in.header)

start = 0
for rec in vcf_in.fetch(contig='21'):
  start = rec.pos
  break
print(start)

end = 0
for rec in vcf_in.fetch(contig='21', start=27148269):
    end = rec.pos
    # vcf_out.write(rec)

print(end)


