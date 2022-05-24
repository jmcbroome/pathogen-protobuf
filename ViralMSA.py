#! /usr/bin/env python3
'''
ViralMSA: Reference-guided multiple sequence alignment of viral genomes
'''

# imports
from Bio import Entrez
from datetime import datetime
from gzip import open as gopen
from hashlib import md5
from io import BufferedReader, TextIOWrapper
from json import load as jload
from math import log2
from multiprocessing import cpu_count
from os import chdir, getcwd, makedirs, remove
from os.path import abspath, expanduser, isdir, isfile, split
from shutil import copy, move
from subprocess import call, CalledProcessError, check_output, DEVNULL, PIPE, Popen, run, STDOUT
from sys import argv, stderr, stdout
from urllib.request import urlopen
import argparse

# useful constants
VERSION = '1.1.21'
RELEASES_URL = 'https://api.github.com/repos/niemasd/ViralMSA/tags'
CIGAR_LETTERS = {'M','D','I','S','H','=','X'}
DEFAULT_BUFSIZE = 1048576 # 1 MB #8192 # 8 KB
DEFAULT_ALIGNER = 'minimap2'
DEFAULT_THREADS = cpu_count()
global LOGFILE; LOGFILE = None

# read mappers that output PAF
ALIGNERS_PAF = {
    'minigraph',
}

# citations
CITATION = {
    'bowtie2':   'Bowtie2: Langmead B, Salzberg SL (2012). "Fast gapped-read alignment with Bowtie 2." Nat Methods. 9(4):357-359. doi:10.1038/nmeth.1923',
    'dragmap':   'DRAGMAP: https://github.com/Illumina/DRAGMAP',
    'hisat2':    'HISAT2: Kim D, Paggi JM, Park C, Bennett C, Salzberg SL (2019). "Graph-based genome alignment and genotyping with HISAT2 and HISAT-genotype." Nat Biotechnol. 37:907-915. doi:10.1038/s41587-019-0201-4',
    'lra':       'LRA: Ren J, Chaisson MJP (2021). "lra: A long read aligner for sequences and contigs." PLoS Comput Biol. 17(6):e1009078. doi:10.1371/journal.pcbi.1009078',
    'minigraph': 'Minigraph: https://github.com/lh3/minigraph',
    'minimap2':  'Minimap2: Li H (2018). "Minimap2: pairwise alignment for nucleotide sequences." Bioinformatics. 34(18):3094-3100. doi:10.1093/bioinformatics/bty191',
    'ngmlr':     'NGMLR: Sedlazeck FJ, Rescheneder P, Smolka M, Fang H, Nattestad M, von Haeseler A, Schatz MC (2018). "Accurate detection of complex structural variations using single-molecule sequencing." Nat Methods. 15:461-468. doi:10.1038/s41592-018-0001-7',
    'star':      'STAR: Dobin A, Davis CA, Schlesinger F, Drehkow J, Zaleski C, Jha S, Batut P, Chaisson M, Gingeras TR (2013). "STAR: ultrafast universal RNA-seq aligner." Bioinformatics. 29(1):15-21. doi:10.1093/bioinformatics/bts635',
    'unimap':    'Unimap: Li H (2021). "Unimap: A fork of minimap2 optimized for assembly-to-reference alignment." https://github.com/lh3/unimap',
    'viralmsa':  'ViralMSA: Moshiri N (2021). "ViralMSA: Massively scalable reference-guided multiple sequence alignment of viral genomes." Bioinformatics. 37(5):714–716. doi:10.1093/bioinformatics/btaa743',
    'wfmash':    'wfmash: Jain C, Koren S, Dilthey A, Phillippy AM, Aluru S (2018). "A Fast Adaptive Algorithm for Computing Whole-Genome Homology Maps". Bioinformatics. 34(17):i748-i756. doi:10.1093/bioinformatics/bty597. Marco-Sola S, Moure JC, Moreto M, Espinosa A (2021). "Fast gap-affine pairwise alignment using the wavefront algorithm". Bioinformatics. 37(4):456-463. doi:10.1093/bioinformatics/btaa777',
}

# reference genomes for common viruses
REFS = {
    'bombalivirus':    'NC_039345', # Bombali Virus (Bombali ebolavirus)
    'bundibugyovirus': 'NC_014373', # Bundibugyo Virus (Bundibugyo ebolavirus)
    'hcv1':            'NC_004102', # HCV genotype 1
    'hcv1h77':         'NC_038882', # HCV genotpye 1 (isolate H77)
    'hcv2':            'NC_009823', # HCV genotype 2
    'hcv3':            'NC_009824', # HCV genotype 3
    'hcv4':            'NC_009825', # HCV genotype 4
    'hcv5':            'NC_009826', # HCV genotype 5
    'hcv6':            'NC_009827', # HCV genotype 6
    'hcv7':            'NC_030791', # HCV genotype 7
    'hiv1':            'NC_001802', # HIV-1
    'hiv2':            'NC_001722', # HIV-2
    'ebolavirus':      'NC_002549', # Ebola Virus (Zaire ebolavirus)
    'restonvirus':     'NC_004161', # Reston Virus (Reston ebolavirus)
    'sarscov2':        'NC_045512', # SARS-CoV-2 (COVID-19)
    'sudanvirus':      'NC_006432', # Sudan Virus (Sudan ebolavirus)
    'taiforestvirus':  'NC_014372', # Tai Forest Virus (Tai Forest ebolavirus, Cote d'Ivoire ebolavirus)
}
REF_NAMES = {
    'Ebola': {
        'bombalivirus':    'Bombali Virus (Bombali ebolavirus)',
        'bundibugyovirus': 'Bundibugyo Virus (Bundibugyo ebolavirus)',
        'ebolavirus':      'Ebola Virus (Zaire ebolavirus)',
        'restonvirus':     'Reston Virus (Reston ebolavirus)',
        'sudanvirus':      'Sudan Virus (Sudan ebolavirus)',
        'taiforestvirus':  'Tai Forest Virus (Tai Forest ebolavirus, Cote d\'Ivoire ebolavirus)',
    },

    'HCV': {
        'hcv1':            'HCV genotype 1',
        'hcv1h77':         'HCV genotpye 1 (isolate H77)',
        'hcv2':            'HCV genotype 2',
        'hcv3':            'HCV genotype 3',
        'hcv4':            'HCV genotype 4',
        'hcv5':            'HCV genotype 5',
        'hcv6':            'HCV genotype 6',
        'hcv7':            'HCV genotype 7',
    },
    
    'HIV': {
        'hiv1':            'HIV-1',
    },
    
    'SARS-CoV-2': {
        'sarscov2':        'SARS-CoV-2 (COVID-19)',
    }
}

# print to long (prefixed by current time)
def print_log(s='', end='\n'):
    tmp = "[%s] %s" % (get_time(), s)
    print(tmp, end=end); stdout.flush()
    if LOGFILE is not None:
        print(tmp, file=LOGFILE, end=end); LOGFILE.flush()

# convert a ViralMSA version string to a tuple of integers
def parse_version(s):
    return tuple(int(v) for v in s.split('.'))

# update ViralMSA to the newest version
def update_viralmsa():
    tags = jload(urlopen(RELEASES_URL))
    newest = max(tags, key=lambda x: parse_version(x['name']))
    if parse_version(newest['name']) <= parse_version(VERSION):
        print("ViralMSA is already at the newest version (%s)" % VERSION); exit(0)
    old_version = VERSION; new_version = newest['name']
    url = 'https://raw.githubusercontent.com/niemasd/ViralMSA/%s/ViralMSA.py' % newest['commit']['sha']
    content = urlopen(url).read()
    try:
        with open(__file__, 'wb') as f:
            f.write(content)
    except PermissionError:
        print("ERROR: Received a permission error when updating ViralMSA. Perhaps try running as root?", file=stderr); exit(1)
    print("Successfully updated ViralMSA %s --> %s" % (old_version, new_version)); exit(0)

# return the current time as a string
def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# count the number of IDs in a FASTA file
def count_IDs_fasta(fn, bufsize=DEFAULT_BUFSIZE):
    return sum(l.startswith('>') for l in open(fn, buffering=bufsize))

# parse a CIGAR string
def parse_cigar(s):
    out = list(); ind = len(s)-1
    while ind >= 0:
        let = s[ind]; ind -= 1; num = ''
        while s[ind] not in CIGAR_LETTERS:
            num += s[ind]; ind -= 1
        out.append((let, int(num[::-1])))
    return out[::-1]

# convert FASTA to FASTQ
def fasta2fastq(fa_path, fq_path, qual='~', bufsize=DEFAULT_BUFSIZE):
    if fa_path.lower().endswith('.gz'):
        fa_file = TextIOWrapper(BufferedReader(gopen(fa_path, 'rb', buffering=bufsize)))
    else:
        fa_file = open(fa_path, 'r', buffering=bufsize)
    if fq_path.lower().endswith('.gz'):
        gzip_out = True; fq_file = gopen(fq_path, 'wb', 9)
    else:
        gzip_out = False; fq_file = open(fq_path, 'w', buffering=bufsize)
    seq_len = 0
    for line_num, line in enumerate(fa_file):
        if line.startswith('>'):
            if line_num == 0:
                curr = '@%s\n' % line[1:].rstrip()
            else:
                curr = '\n+\n%s\n@%s\n' % (qual*seq_len, line[1:].rstrip()); seq_len = 0
        else:
            curr = line.rstrip(); seq_len += len(curr)
        if gzip_out:
            fq_file.write(curr.encode())
        else:
            fq_file.write(curr)
    curr = '\n+\n%s\n' % (qual*seq_len)
    if gzip_out:
        fq_file.write(curr.encode())
    else:
        fq_file.write(curr)

# check bowtie2
def check_bowtie2():
    try:
        o = check_output(['bowtie2', '-h'])
    except:
        o = None
    if o is None or 'Bowtie 2 version' not in o.decode():
        print("ERROR: bowtie2 is not runnable in your PATH", file=stderr); exit(1)
    try:
        o = check_output(['bowtie2-build', '-h'])
    except:
        o = None
    if o is None or 'Bowtie 2 version' not in o.decode():
        print("ERROR: bowtie2-build is not runnable in your PATH", file=stderr); exit(1)

# check DRAGMAP
def check_dragmap():
    try:
        o = check_output(['dragen-os', '-h'])
    except:
        o = None
    if o is None or 'dragenos -r <reference> -b <base calls> [optional arguments]' not in o.decode():
        print("ERROR: dragen-os is not runnable in your PATH", file=stderr); exit(1)

# check HISAT2
def check_hisat2():
    try:
        o = check_output(['hisat2', '-h'])
    except:
        o = None
    if o is None or 'HISAT2 version' not in o.decode():
        print("ERROR: hisat2 is not runnable in your PATH", file=stderr); exit(1)
    try:
        o = check_output(['hisat2-build', '-h'])
    except:
        o = None
    if o is None or 'HISAT2 version' not in o.decode():
        print("ERROR: hisat2-build is not runnable in your PATH", file=stderr); exit(1)

# check LRA
def check_lra():
    try:
        o = check_output(['lra', '-h'])
    except CalledProcessError as cpe:
        o = cpe.output
    except:
        o = None
    if o is None or 'lra (long sequence alignment)' not in o.decode():
        print(o.decode())
        print("ERROR: LRA is not runnable in your PATH", file=stderr); exit(1)

# check minigraph
def check_minigraph():
    try:
        o = run(['minigraph'], stdout=PIPE, stderr=PIPE).stderr
    except:
        o = None
    if o is None or 'Usage: minigraph' not in o.decode():
        print("ERROR: Minigraph is not runnable in your PATH", file=stderr); exit(1)

# check minimap2
def check_minimap2():
    try:
        o = check_output(['minimap2', '-h'])
    except:
        o = None
    if o is None or 'Usage: minimap2' not in o.decode():
        print("ERROR: Minimap2 is not runnable in your PATH", file=stderr); exit(1)

# check NGMLR
def check_ngmlr():
    try:
        o = check_output(['ngmlr', '-h'], stderr=STDOUT)
    except:
        o = None
    if o is None or 'Usage: ngmlr' not in o.decode():
        print("ERROR: NGMLR is not runnable in your PATH", file=stderr); exit(1)

# check STAR
def check_star():
    try:
        o = check_output(['STAR', '-h'])
    except:
        o = None
    if o is None or 'Usage: STAR' not in o.decode():
        print("ERROR: STAR is not runnable in your PATH", file=stderr); exit(1)

# check unimap
def check_unimap():
    try:
        o = check_output(['unimap', '-h'])
    except:
        o = None
    if o is None or 'Usage: unimap' not in o.decode():
        print("ERROR: Unimap is not runnable in your PATH", file=stderr); exit(1)

# check wfmash
def check_wfmash():
    try:
        o = check_output(['wfmash', '-h'])
    except:
        o = None
    if o is None or 'wfmash [target] [queries...] {OPTIONS}' not in o.decode():
        print("ERROR: wfmash is not runnable in your PATH", file=stderr); exit(1)

# build FAIDX index (multiple tools might need this)
def build_index_faidx(ref_genome_path, threads, verbose=True):
    index_path = '%s.fai' % ref_genome_path
    if isfile(index_path):
        if verbose:
            print_log("FAIDX index found: %s" % index_path)
        return
    command = ['samtools', 'faidx', ref_genome_path]
    if verbose:
        print_log("Building FAIDX index: %s" % ' '.join(command))
    log = open('%s.log' % index_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        print_log("FAIDX index built: %s" % index_path)

# build bowtie2 index
def build_index_bowtie2(ref_genome_path, threads, verbose=True):
    exts = ['1.bt2', '2.bt2', '3.bt2', '4.bt2', 'rev.1.bt2', 'rev.2.bt2']
    all_found = True
    for ext in exts:
        if not isfile('%s.bowtie2.%s' % (ref_genome_path,ext)):
            all_found = False; break
    if all_found:
        if verbose:
            print_log("bowtie2 index found: %s.bowtie2.*.bt2" % ref_genome_path)
        return
    for ext in exts:
        if isfile('%s.bowtie2.%s' % (ref_genome_path,ext)):
            remove('%s.bowtie2.%s' % (ref_genome_path,ext))
    ref_genome_dir, ref_genome_fn = split(ref_genome_path)
    orig_dir = getcwd()
    chdir(ref_genome_dir)
    command = ['bowtie2-build', '--threads', str(threads), ref_genome_path, '%s.bowtie2' % ref_genome_fn]
    if verbose:
        print_log("Building bowtie2 index: %s" % ' '.join(command))
    log = open('%s.bowtie2.log' % ref_genome_path, 'w'); call(command, stdout=log, stderr=STDOUT); log.close()
    if verbose:
        print_log("bowtie2 index built: %s.bowtie2.*.bt2" % ref_genome_path)
    chdir(orig_dir)

# build DRAGMAP index
def build_index_dragmap(ref_genome_path, threads, verbose=True):
    index_path = '%s.DRAGMAP' % ref_genome_path
    if isdir(index_path):
        if verbose:
            print_log("DRAGMAP index found: %s" % index_path)
        return
    makedirs(index_path, exist_ok=False)
    command = ['dragen-os', '--build-hash-table', 'true', '--ht-reference', ref_genome_path, '--ht-num-threads', str(threads), '--output-directory', index_path]
    if verbose:
        print_log("Building DRAGMAP index: %s" % ' '.join(command))
    log = open('%s/index.log' % index_path, 'w'); call(command, stdout=log, stderr=STDOUT); log.close()
    if verbose:
        print_log("DRAGMAP index built: %s" % index_path)

# build HISAT2 index
def build_index_hisat2(ref_genome_path, threads, verbose=True):
    exts = [('%d.ht2'%i) for i in range(1,9)]
    all_found = True
    for ext in exts:
        if not isfile('%s.hisat2.%s' % (ref_genome_path,ext)):
            all_found = False; break
    if all_found:
        if verbose:
            print_log("HISAT2 index found: %s.hisat2.*.ht2" % ref_genome_path)
        return
    for ext in exts:
        if isfile('%s.hisat2.%s' % (ref_genome_path,ext)):
            remove('%s.hisat2.%s' % (ref_genome_path,ext))
    ref_genome_dir, ref_genome_fn = split(ref_genome_path)
    orig_dir = getcwd()
    chdir(ref_genome_dir)
    command = ['hisat2-build', '--threads', str(threads), ref_genome_path, '%s.hisat2' % ref_genome_fn]
    if verbose:
        print_log("Building HISAT2 index: %s" % ' '.join(command))
    log = open('%s.hisat2.log' % ref_genome_path, 'w'); call(command, stdout=log, stderr=STDOUT); log.close()
    if verbose:
        print_log("HISAT2 index built: %s.hisat2.*.ht2" % ref_genome_path)
    chdir(orig_dir)

# build LRA index
def build_index_lra(ref_genome_path, threads, verbose=True):
    lra_ref_genome_path = '%s.lra' % ref_genome_path
    gli_index_path = '%s.gli' % lra_ref_genome_path
    mmi_index_path = '%s.mmi' % lra_ref_genome_path
    mms_index_path = '%s.mms' % lra_ref_genome_path
    if isfile(lra_ref_genome_path) and isfile(gli_index_path) and (isfile(mmi_index_path) or isfile(mms_index_path)):
        if verbose:
            if isfile(mmi_index_path):
                print_log("LRA index files found: %s and %s" % (gli_index_path, mmi_index_path))
            else:
                print_log("LRA index files found: %s and %s" % (gli_index_path, mms_index_path))
        return
    elif isfile(lra_ref_genome_path):
        raise RuntimeError("Corrupt LRA index. Please delete the following and try again: %s" % lra_ref_genome_path)
    elif isfile(gli_index_path):
        raise RuntimeError("Corrupt LRA index. Please delete the following and try again: %s" % gli_index_path)
    elif isfile(mmi_index_path):
        raise RuntimeError("Corrupt LRA index. Please delete the following and try again: %s" % mmi_index_path)
    elif isfile(mms_index_path):
        raise RuntimeError("Corrupt LRA index. Please delete the following and try again: %s" % mms_index_path)
    copy(ref_genome_path, lra_ref_genome_path)
    command = ['lra', 'index', '-CONTIG', lra_ref_genome_path]
    if verbose:
        print_log("Building LRA index: %s" % ' '.join(command))
    log = open('%s.log' % lra_ref_genome_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        if isfile(mmi_index_path):
            print_log("LRA index built: %s and %s" % (gli_index_path, mmi_index_path))
        else:
            print_log("LRA index built: %s and %s" % (gli_index_path, mms_index_path))

# build minigraph index
def build_index_minigraph(ref_genome_path, threads, verbose=True):
    pass # Minigraph doesn't seem to do anything with a ref genome with 1 sequence

# build minimap2 index
def build_index_minimap2(ref_genome_path, threads, verbose=True):
    index_path = '%s.mmi' % ref_genome_path
    if isfile(index_path):
        if verbose:
            print_log("Minimap2 index found: %s" % index_path)
        return
    command = ['minimap2', '-t', str(threads), '-d', index_path, ref_genome_path]
    if verbose:
        print_log("Building Minimap2 index: %s" % ' '.join(command))
    log = open('%s.log' % index_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        print_log("Minimap2 index built: %s" % index_path)

# build NGMLR index
def build_index_ngmlr(ref_genome_path, threads, verbose=True):
    enc_index_path = '%s-enc.2.ngm' % ref_genome_path
    ht_index_path = '%s-ht-13-2.2.ngm' % ref_genome_path
    if isfile(enc_index_path) and isfile(ht_index_path):
        if verbose:
            print_log("NGMLR index files found: %s and %s" % (enc_index_path, ht_index_path))
        return
    elif isfile(enc_index_path):
        raise RuntimeError("Corrupt NGMLR index. Please delete the following and try again: %s" % enc_index_path)
    elif isfile(ht_index_path):
        raise RuntimeError("Corrupt NGMLR index. Please delete the following and try again: %s" % ht_index_path)
    command = ['ngmlr', '-x', 'pacbio', '-i', '0', '--no-smallinv', '-t', str(threads), '-r', ref_genome_path]
    if verbose:
        print_log("Building NGMLR index: %s" % ' '.join(command))
    log = open('%s.NGMLR.log' % ref_genome_path, 'w'); call(command, stdin=DEVNULL, stderr=log, stdout=DEVNULL); log.close()
    if verbose:
        print_log("NGMLR index built: %s and %s" % (enc_index_path, ht_index_path))

# build STAR index
def build_index_star(ref_genome_path, threads, verbose=True):
    delete_log = True # STAR by default creates Log.out in the running directory
    if isfile('Log.out'):
        delete_log = False # don't delete it (it existed before running ViralMSA)
    index_path = '%s.STAR' % ref_genome_path
    if isdir(index_path):
        if verbose:
            print_log("STAR index found: %s" % index_path)
        return
    genome_length = sum(len(l.strip()) for l in open(ref_genome_path) if not l.startswith('>'))
    genomeSAindexNbases = min(14, int(log2(genome_length)/2)-1)
    makedirs(index_path, exist_ok=False)
    command = ['STAR', '--runMode', 'genomeGenerate', '--runThreadN', str(threads), '--genomeDir', index_path, '--genomeFastaFiles', ref_genome_path, '--genomeSAindexNbases', str(genomeSAindexNbases)]
    if verbose:
        print_log("Building STAR index: %s" % ' '.join(command))
    log = open('%s/index.log' % index_path, 'w'); call(command, stdout=log, stderr=STDOUT); log.close()
    if verbose:
        print_log("STAR index built: %s" % index_path)
    if delete_log and isfile('Log.out'):
        remove('Log.out')

# build unimap index
def build_index_unimap(ref_genome_path, threads, verbose=True):
    index_path = '%s.umi' % ref_genome_path
    if isfile(index_path):
        if verbose:
            print_log("Unimap index found: %s" % index_path)
        return
    command = ['unimap', '-t', str(threads), '-d', index_path, ref_genome_path]
    if verbose:
        print_log("Building Unimap index: %s" % ' '.join(command))
    log = open('%s.log' % index_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        print_log("Unimap index built: %s" % index_path)

# build wfmash index
def build_index_wfmash(ref_genome_path, threads, verbose=True):
    build_index_faidx(ref_genome_path, threads, verbose=True)

# align genomes using bowtie2
def align_bowtie2(seqs_path, out_aln_path, ref_genome_path, threads, verbose=True):
    command = ['bowtie2', '--very-sensitive', '-p', str(threads), '-f', '-x', '%s.bowtie2' % ref_genome_path, '-U', seqs_path, '-S', out_aln_path]
    if verbose:
        print_log("Aligning using bowtie2: %s" % ' '.join(command))
    log = open('%s.log' % out_aln_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        print_log("bowtie2 alignment complete: %s" % out_aln_path)

# align genomes using DRAGMAP
def align_dragmap(seqs_path, out_aln_path, ref_genome_path, threads, verbose=True):
    tmp_fq_path = '%s.fastq.gz' % out_aln_path
    fasta2fastq(seqs_path, tmp_fq_path)
    command = ['dragen-os', '--num-threads', str(threads), '--Aligner.sw-all', '1', '-r', '%s.DRAGMAP' % ref_genome_path, '-1', tmp_fq_path]
    if verbose:
        print_log("Aligning using DRAGMAP: %s" % ' '.join(command))
    out = open(out_aln_path, 'w'); log = open('%s.log' % out_aln_path, 'w'); call(command, stdout=out, stderr=log); out.close(); log.close()
    if verbose:
        print_log("DRAGMAP alignment complete: %s" % out_aln_path)

# align genomes using HISAT2
def align_hisat2(seqs_path, out_aln_path, ref_genome_path, threads, verbose=True):
    command = ['hisat2', '--very-sensitive', '-p', str(threads), '-f', '-x', '%s.hisat2' % ref_genome_path, '-U', seqs_path, '-S', out_aln_path]
    if verbose:
        print_log("Aligning using HISAT2: %s" % ' '.join(command))
    log = open('%s.log' % out_aln_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        print_log("HISAT2 alignment complete: %s" % out_aln_path)

# align genomes using LRA
def align_lra(seqs_path, out_aln_path, ref_genome_path, threads, verbose=True):
    lra_ref_genome_path = '%s.lra' % ref_genome_path
    command = ['lra', 'align', '-t', str(threads), '-CONTIG', '-p', 's', lra_ref_genome_path, seqs_path]
    if verbose:
        print_log("Aligning using LRA: %s" % ' '.join(command))
    out_sam_file = open(out_aln_path, 'w'); log = open('%s.log' % out_aln_path, 'w'); call(command, stdout=out_sam_file, stderr=log); out_sam_file.close(); log.close()
    if verbose:
        print_log("LRA alignment complete: %s" % out_aln_path)

# align genomes using minigraph
def align_minigraph(seqs_path, out_paf_path, ref_genome_path, threads, verbose=True):
    command = ['minigraph', '-c', '-t', str(threads), '--secondary=no', '-l', '0', '-d', '0', '-L', '0', '-o', out_paf_path, ref_genome_path, seqs_path]
    if verbose:
        print_log("Aligning using Minigraph: %s" % ' '.join(command))
    log = open('%s.log' % out_paf_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        print_log("Minigraph alignment complete: %s" % out_paf_path)

# align genomes using minimap2
def align_minimap2(seqs_path, out_aln_path, ref_genome_path, threads, verbose=True):
    index_path = '%s.mmi' % ref_genome_path
    command = ['minimap2', '-t', str(threads), '--score-N=0', '--secondary=no', '--sam-hit-only', '-a', '-o', out_aln_path, index_path, seqs_path]
    if verbose:
        print_log("Aligning using Minimap2: %s" % ' '.join(command))
    log = open('%s.log' % out_aln_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        print_log("Minimap2 alignment complete: %s" % out_aln_path)

# align genomes using NGMLR
def align_ngmlr(seqs_path, out_aln_path, ref_genome_path, threads, verbose=True):
    command = ['ngmlr', '--skip-write', '-x', 'pacbio', '-i', '0', '--no-smallinv', '-t', str(threads), '-r', ref_genome_path, '-q', seqs_path, '-o', out_aln_path]
    if verbose:
        print_log("Aligning using NGMLR: %s" % ' '.join(command))
    log = open('%s.log' % out_aln_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        print_log("NGMLR alignment complete: %s" % out_aln_path)

# align genomes using STAR
def align_star(seqs_path, out_aln_path, ref_genome_path, threads, verbose=True):
    delete_log = True # STAR by default creates Log.out in the running directory
    if isfile('Log.out'):
        delete_log = False # don't delete it (it existed before running ViralMSA)
    index_path = '%s.STAR' % ref_genome_path
    out_sam_dir, out_sam_fn = split(out_aln_path)
    out_file_prefix = '%s.' % '.'.join(out_aln_path.split('.')[:-1])
    command = ['STAR', '--runThreadN', str(threads), '--genomeDir', index_path, '--readFilesIn', seqs_path, '--outFileNamePrefix', out_file_prefix, '--outFilterMismatchNmax', '9999999999']
    if verbose:
        print_log("Aligning using STAR: %s" % ' '.join(command))
    log = open('%s/STAR.log' % out_sam_dir, 'w'); call(command, stdout=log); log.close()
    move('%sAligned.out.sam' % out_file_prefix, out_aln_path)
    if verbose:
        print_log("STAR alignment complete: %s" % out_sam_dir)
    if delete_log and isfile('Log.out'):
        remove('Log.out')

# align genomes using unimap
def align_unimap(seqs_path, out_aln_path, ref_genome_path, threads, verbose=True):
    index_path = '%s.umi' % ref_genome_path
    command = ['unimap', '-t', str(threads), '--score-N=0', '--secondary=no', '--sam-hit-only', '-a', '--cs', '-o', out_aln_path, index_path, seqs_path]
    if verbose:
        print_log("Aligning using Unimap: %s" % ' '.join(command))
    log = open('%s.log' % out_aln_path, 'w'); call(command, stderr=log); log.close()
    if verbose:
        print_log("Unimap alignment complete: %s" % out_aln_path)

# align genomes using wfmash
def align_wfmash(seqs_path, out_aln_path, ref_genome_path, threads, verbose=True):
    ref_genome_length = sum(len(l.strip()) for l in open(ref_genome_path) if not l.startswith('>'))
    command = ['wfmash', '-N', '--sam-format', '--threads=%d' % threads, ref_genome_path, seqs_path]
    if verbose:
        print_log("Aligning using wfmash: %s" % ' '.join(command))
    sam = open(out_aln_path, 'w'); log = open('%s.log' % out_aln_path, 'w'); call(command, stdout=sam, stderr=log); sam.close(); log.close()
    if verbose:
        print_log("wfmash alignment complete: %s" % out_aln_path)

# aligners
ALIGNERS = {
    'bowtie2': {
        'check':       check_bowtie2,
        'build_index': build_index_bowtie2,
        'align':       align_bowtie2,
    },

    'dragmap': {
        'check':       check_dragmap,
        'build_index': build_index_dragmap,
        'align':       align_dragmap,
    },

    'hisat2': {
        'check':       check_hisat2,
        'build_index': build_index_hisat2,
        'align':       align_hisat2,
    },

    'lra': {
        'check':       check_lra,
        'build_index': build_index_lra,
        'align':       align_lra,
    },

    # Minigraph still doesn't work (only outputs PAF without sequences)
    #'minigraph': {
    #    'check':       check_minigraph,
    #    'build_index': build_index_minigraph,
    #    'align':       align_minigraph,
    #},

    'minimap2': {
        'check':       check_minimap2,
        'build_index': build_index_minimap2,
        'align':       align_minimap2,
    },

    'ngmlr': {
        'check':       check_ngmlr,
        'build_index': build_index_ngmlr,
        'align':       align_ngmlr,
    },

    'star': {
        'check':       check_star,
        'build_index': build_index_star,
        'align':       align_star,
    },

    'unimap': {
        'check':       check_unimap,
        'build_index': build_index_unimap,
        'align':       align_unimap,
    },

    'wfmash': {
        'check':       check_wfmash,
        'build_index': build_index_wfmash,
        'align':       align_wfmash,
    },
}

# handle GUI (updates argv)
def run_gui():
    def clear_argv():
        tmp = argv[0]; argv.clear(); argv.append(tmp)
    try:
        # imports
        from tkinter import Button, Checkbutton, END, Entry, Frame, IntVar, Label, OptionMenu, StringVar, Tk
        from tkinter.filedialog import askdirectory, askopenfilename

        # helper function to make a popup
        def gui_popup(message, title=None):
            popup = Tk()
            if title:
                popup.wm_title(title)
            label = Label(popup, text=message)
            label.pack()
            button_close = Button(popup, text="Close", command=popup.destroy)
            button_close.pack(padx=3, pady=3)
            popup.mainloop()

        # create applet
        root = Tk()
        root.geometry("600x400")
        #root.configure(background='white')

        # set up main frame
        frame = Frame(root)
        frame.pack()

        # add header
        header = Label(frame, text="ViralMSA %s" % VERSION, font=('Arial',24))
        header.pack()

        # handle input FASTA selection
        button_seqs_prefix = "Input Sequences:\n"
        button_seqs_nofile = "<none selected>"
        def find_filename_seqs():
            fn = askopenfilename(title="Select Input Sequences (FASTA format)",filetypes=(("FASTA Files",("*.fasta","*.fas")),("All Files","*.*")))
            if len(fn) == 0:
                button_seqs.configure(text="%s%s" % (button_seqs_prefix,button_seqs_nofile))
            else:
                button_seqs.configure(text="%s%s" % (button_seqs_prefix,fn))
        button_seqs = Button(frame, text="%s%s" % (button_seqs_prefix,button_seqs_nofile), command=find_filename_seqs)
        button_seqs.pack(padx=3, pady=3)

        # handle reference
        dropdown_ref_default = "Select Reference"
        dropdown_ref_var = StringVar(frame)
        dropdown_ref_var.set(dropdown_ref_default)
        dropdown_ref = OptionMenu(frame, dropdown_ref_var, *sorted(REF_NAMES[k][v] for k in REF_NAMES for v in REF_NAMES[k]))
        dropdown_ref.pack()

        # handle user email
        entry_email_default = "Enter Email Address"
        entry_email = Entry(frame, width=30)
        entry_email.insert(END, entry_email_default)
        entry_email.pack()

        # handle output folder selection
        button_out_prefix = "Output Directory:\n"
        button_out_nofolder = "<none selected>"
        def find_directory_out():
            dn = askdirectory(title="Select Output Directory")
            if len(dn) == 0:
                button_out.configure(text="%s%s" % (button_out_prefix,button_out_nofolder))
            else:
                button_out.configure(text="%s%s" % (button_out_prefix,dn))
        button_out = Button(frame, text="%s%s" % (button_out_prefix,button_out_nofolder), command=find_directory_out)
        button_out.pack(padx=3, pady=3)

        # handle aligner selection
        dropdown_aligner_prefix = "Aligner: "
        dropdown_aligner_var = StringVar(frame)
        dropdown_aligner_var.set("%s%s" % (dropdown_aligner_prefix,DEFAULT_ALIGNER.lower()))
        dropdown_aligner = OptionMenu(frame, dropdown_aligner_var, *sorted(("%s%s" % (dropdown_aligner_prefix,a)) for a in ALIGNERS))
        dropdown_aligner.pack()

        # handle threads selection
        dropdown_threads_prefix = "Threads: "
        dropdown_threads_var = StringVar(frame)
        dropdown_threads_var.set("%s%s" % (dropdown_threads_prefix,DEFAULT_THREADS))
        dropdown_threads = OptionMenu(frame, dropdown_threads_var, *[("%s%d" % (dropdown_threads_prefix,i)) for i in range(1,DEFAULT_THREADS+1)])
        dropdown_threads.pack()

        # handle omit reference toggle
        check_omitref_var = IntVar(frame)
        check_omitref = Checkbutton(frame, text="Omit reference sequence from output MSA", variable=check_omitref_var, onvalue=1, offvalue=0)
        check_omitref.pack()

        # add run button
        def finish_applet():
            valid = True
            # check sequences
            try:
                if button_seqs['text'] == "%s%s" % (button_seqs_prefix,button_seqs_nofile):
                    gui_popup("ERROR: Input Sequences file not selected", title="ERROR"); valid = False
            except:
                pass
            # check reference
            try:
                if dropdown_ref_var.get() == dropdown_ref_default:
                   gui_popup("ERROR: Reference not selected", title="ERROR"); valid = False
            except:
                pass
            # check email
            try:
                if '@' not in entry_email.get():
                    gui_popup("ERROR: Email Address not entered", title="ERROR"); valid = False
            except:
                pass
            # check output directory
            try:
                if button_out['text'] == "%s%s" % (button_out_prefix,button_out_nofolder):
                    gui_popup("ERROR: Output Directory not selected", title="ERROR"); valid = False
                elif isdir(button_out['text'].lstrip(button_out_prefix).strip()):
                    gui_popup("ERROR: Output Directory already exists", title="ERROR"); valid = False
            except:
                pass
            # close applet to run ViralMSA
            if valid:
                argv.append('-s'); argv.append(button_seqs['text'].lstrip(button_seqs_prefix).strip())
                argv.append('-r'); argv.append([v for k in REF_NAMES for v in REF_NAMES[k] if REF_NAMES[k][v] == dropdown_ref_var.get()][0])
                argv.append('-e'); argv.append(entry_email.get())
                argv.append('-o'); argv.append(button_out['text'].lstrip(button_out_prefix).strip())
                argv.append('-a'); argv.append(dropdown_aligner_var.get().lstrip(dropdown_aligner_prefix).strip())
                argv.append('-t'); argv.append(dropdown_threads_var.get().lstrip(dropdown_threads_prefix).strip())
                if check_omitref_var.get() == 1:
                    argv.append('--omit_ref')
                try:
                    root.destroy()
                except:
                    pass
        button_run = Button(frame, text="Run", command=finish_applet)
        button_run.pack(padx=3, pady=3)

        # add title and execute GUI
        root.title("ViralMSA %s" % VERSION)
        root.mainloop()
    except:
        print("ERROR: Unable to import Tkinter", file=stderr); exit(1)
    if len(argv) == 1:
        exit()

# parse user args
def parse_args():
    # check if user wants to run the GUI
    if len(argv) == 1:
        run_gui()

    # check if user wants to update ViralMSA
    if '-u' in argv or '--update' in argv:
        update_viralmsa()

    # check if user just wants to list references
    if '-l' in argv or '--list_references' in argv:
        print("=== List of ViralMSA Reference Sequences ===")
        for v in sorted(REF_NAMES.keys()):
            print("* %s" % v)
            for r in sorted(REF_NAMES[v].keys()):
                print("  - %s: %s" % (r, REF_NAMES[v][r]))
        exit(0)

    # use argparse to parse user arguments
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', '--sequences', required=True, type=str, help="Input Sequences (FASTA format)")
    parser.add_argument('-r', '--reference', required=True, type=str, help="Reference")
    parser.add_argument('-e', '--email', required=True, type=str, help="Email Address (for Entrez)")
    parser.add_argument('-o', '--output', required=True, type=str, help="Output Directory")
    parser.add_argument('-a', '--aligner', required=False, type=str, default=DEFAULT_ALIGNER, help="Aligner (options: %s)" % ', '.join(sorted(ALIGNERS.keys())))
    parser.add_argument('-t', '--threads', required=False, type=int, default=DEFAULT_THREADS, help="Number of Threads")
    parser.add_argument('-b', '--buffer_size', required=False, type=int, default=DEFAULT_BUFSIZE, help="File Stream Buffer Size (bytes)")
    parser.add_argument('-l', '--list_references', action="store_true", help="List all reference sequences")
    parser.add_argument('--omit_ref', action="store_true", help="Omit reference sequence from output alignment")
    parser.add_argument('--viralmsa_dir', required=False, type=str, default=abspath(expanduser("~/.viralmsa")), help="ViralMSA Cache Directory")
    parser.add_argument('-u', '--update', action="store_true", help="Update ViralMSA (current version: %s)" % VERSION)
    args = parser.parse_args()

    # check user args for validity
    if args.threads < 1:
        print("ERROR: Number of threads must be positive", file=stderr); exit(1)
    if args.buffer_size < 1:
        print("ERROR: Output buffer size must be positive", file=stderr); exit(1)
    args.aligner = args.aligner.lower()
    if args.aligner not in ALIGNERS:
        print("ERROR: Invalid aligner: %s (valid options: %s)" % (args.aligner, ', '.join(sorted(ALIGNERS.keys()))), file=stderr); exit(1)
    args.sequences = abspath(expanduser(args.sequences))
    if not isfile(args.sequences):
        print("ERROR: Sequences file not found: %s" % args.sequences, file=stderr); exit(1)
    if args.sequences.lower().endswith('.gz'):
        print("ERROR: Sequences cannot be compressed: %s" % args.sequences, file=stderr); exit(1)
    args.output = abspath(expanduser(args.output))
    if isdir(args.output) or isfile(args.output):
        print("ERROR: Output directory exists: %s" % args.output, file=stderr); exit(1)
    if isfile(args.reference):
        if count_IDs_fasta(args.reference, bufsize=args.buffer_size) != 1:
            print("ERROR: Reference file (%s) must have exactly 1 sequence in the FASTA format" % args.reference, file=stderr); exit(1)
        ref_seq = ''.join(l.strip() for l in open(args.reference, 'r', args.buffer_size) if not l.startswith('>'))
        h = md5(ref_seq.encode()).hexdigest()
        fn = args.reference
        args.reference = '%s_HASH_%s' % (fn.split('/')[-1].strip(), h)
        args.ref_path = '%s/%s' % (args.viralmsa_dir, args.reference)
        args.ref_genome_path = '%s/%s' % (args.ref_path, fn.split('/')[-1].strip())
        if not isdir(args.ref_path):
            makedirs(args.ref_path)
            copy(fn, args.ref_genome_path)
    else:
        tmp = args.reference.lower().replace(' ','').replace('-','').replace('_','')
        if tmp in REFS:
            args.reference = REFS[tmp]
        args.reference = args.reference.upper()
        args.ref_path = '%s/%s' % (args.viralmsa_dir, args.reference)
        args.ref_genome_path = '%s/%s.fas' % (args.ref_path, args.reference)

    # user args are valid, so return
    return args

# download reference genome
def download_ref_genome(ref_path, ref_genome_path, email, bufsize=DEFAULT_BUFSIZE):
    makedirs(ref_path, exist_ok=True); Entrez.email = email
    try:
        handle = Entrez.efetch(db='nucleotide', rettype='fasta', id=args.reference)
    except:
        raise RuntimeError("Encountered error when trying to download reference genome from NCBI. Perhaps the accession number is invalid?")
    seq = handle.read()
    if seq.count('>') != 1:
        print("ERROR: Reference genome must only have a single sequence", file=stderr); exit(1)
    f = open(ref_genome_path, 'w', buffering=bufsize); f.write(seq.strip()); f.write('\n'); f.close()

# convert alignment (SAM/PAF) to FASTA
def aln_to_fasta(out_aln_path, out_msa_path, ref_genome_path, bufsize=DEFAULT_BUFSIZE):
    if out_aln_path.lower().endswith('.sam'):
        aln_type = 's' # SAM
    elif out_aln_path.lower().endswith('.paf'):
        aln_type = 'p' # PAF
    else:
        print("ERROR: Invalid alignment extension: %s" % out_aln_path, file=stderr); exit(1)
    msa = open(out_msa_path, 'w', buffering=bufsize); ref_seq = list()
    for line in open(ref_genome_path):
        if len(line) == 0:
            continue
        if line[0] != '>':
            ref_seq.append(line.strip())
        elif not args.omit_ref:
            msa.write(line)
    if not args.omit_ref:
        for l in ref_seq:
            msa.write(l)
        msa.write('\n')
    ref_seq_len = sum(len(l) for l in ref_seq)
    num_output_IDs = 0
    for l in open(out_aln_path):
        if l == '\n' or l[0] == '@':
            continue
        parts = l.split('\t')
        if aln_type == 's': # SAM
            flags = int(parts[1])
            if flags != 0 and flags != 16:
                continue
            ID = parts[0].strip(); num_output_IDs += 1
            ref_ind = int(parts[3])-1
            seq = parts[9].strip()
            cigar = parts[5].strip()
        elif aln_type == 'p': # PAF
            raise RuntimeError("PAF alignments are not yet supported")
        edits = parse_cigar(cigar)
        msa.write(">%s\n" % ID)
        if ref_ind > 0:
            msa.write('-'*ref_ind) # write gaps before alignment
        ind = 0; seq_len = ref_ind
        for e, e_len in edits:
            if e == 'M' or e == '=' or e == 'X': # (mis)match)
                msa.write(seq[ind:ind+e_len])
                ind += e_len; seq_len += e_len
            elif e == 'D':                       # deletion (gap in query)
                msa.write('-'*e_len)
                seq_len += e_len
            elif e == 'I':                       # insertion (gap in reference; ignore)
                ind += e_len
            elif e == 'S' or e == 'H':           # starting/ending segment of query not in reference (i.e., span of insertions; ignore)
                ind += e_len
        if seq_len < ref_seq_len:
            msa.write('-'*(ref_seq_len-seq_len)) # write gaps after alignment
        msa.write('\n')
    msa.close()
    return num_output_IDs

# main content
if __name__ == "__main__":
    # parse user args and prepare run
    args = parse_args()
    makedirs(args.viralmsa_dir, exist_ok=True)
    makedirs(args.output)
    LOGFILE = open("%s/viralmsa.log" % args.output, 'w')
    ALIGNERS[args.aligner]['check']()
    num_input_IDs = count_IDs_fasta(args.sequences, bufsize=args.buffer_size)

    # print run information
    print_log("===== RUN INFORMATION =====")
    print_log("ViralMSA Version: %s" % VERSION)
    print_log("Sequences: %s" % args.sequences)
    print_log("Reference: %s" % args.reference)
    print_log("Email Address: %s" % args.email)
    print_log("Output Directory: %s" % args.output)
    print_log("Aligner: %s" % args.aligner)
    print_log("ViralMSA Cache Directory: %s" % args.viralmsa_dir)
    print_log()

    # download reference genome if not already downloaded
    print_log("===== REFERENCE GENOME =====")
    if isfile(args.ref_genome_path):
        print_log("Reference genome found: %s" % args.ref_genome_path)
    else:
        print_log("Downloading reference genome from NCBI...")
        download_ref_genome(args.ref_path, args.ref_genome_path, args.email, bufsize=args.buffer_size)
        print_log("Reference genome downloaded: %s" % args.ref_genome_path)

    # build aligner index (if needed)
    ALIGNERS[args.aligner]['build_index'](args.ref_genome_path, args.threads)
    print_log()

    # align viral genomes against referencea
    print_log("===== ALIGNMENT =====")
    if args.aligner in ALIGNERS_PAF:
        out_aln_path = '%s/%s.paf' % (args.output, args.sequences.split('/')[-1])
    else:
        out_aln_path = '%s/%s.sam' % (args.output, args.sequences.split('/')[-1])
    ALIGNERS[args.aligner]['align'](args.sequences, out_aln_path, args.ref_genome_path, args.threads)

    # convert alignment (SAM/PAF) to MSA FASTA
    print_log("Converting alignment to FASTA...")
    out_msa_path = '%s/%s.aln' % (args.output, args.sequences.split('/')[-1])
    num_output_IDs = aln_to_fasta(out_aln_path, out_msa_path, args.ref_genome_path, bufsize=args.buffer_size)
    print_log("Multiple sequence alignment complete: %s" % out_aln_path)
    if num_output_IDs < num_input_IDs:
        print_log("WARNING: Some sequences from the input are missing from the output. Perhaps try a different aligner or reference genome?")
    print_log()

    # print citations and finish
    print_log("===== CITATIONS =====")
    print_log(CITATION['viralmsa'])
    print_log(CITATION[args.aligner])
    LOGFILE.close()
