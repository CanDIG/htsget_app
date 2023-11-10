get files and unzip:
https://hgdownload.soe.ucsc.edu/goldenPath/hg19/database/ncbiRefSeqSelect.txt.gz
https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/ncbiRefSeqCurated.txt.gz

run a substitution:
s/^(.+?)\t(.+?)\t(.+?)\t(.)\t(\d+)\t(\d+)\t(\d+)\t(\d+)\t(\d+)\t(.+?)\t(.+?)\t.\t(.+?)\t.+$/\2\t\3\t\5\t\6\t\12/g

now the columns left are:
name, contig, txStart, txEnd, name2
which correspond to our:
transcript_name, contig, start, endpos, gene_name

These files are saved as ncbiRefSeqSelect.hg37.txt and ncbiRefSeqSelect.hg38.txt.