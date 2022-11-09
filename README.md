# pathogen-protobuf
Short pipeline to create MAT Protobuf (.pb) files from Genbank (.gb) or fasta format files.

# Setup
Some dependencies can be installed with conda.

```
conda env create -f environment.yml
```

You will need [minimap2](https://github.com/lh3/minimap2#install) to perform the alignment. We recommend downloading the precompiled binary for your system and adding it to your system path. You will also need [faToVcf](http://hgdownload.soe.ucsc.edu/admin/exe/) for your architecture. Assure that the paths to your dependencies are correct in the config.yaml file.

If you are starting with a Genbank format file instead of a fasta, you will additionally need gbmunge.

```
git clone https://github.com/sdwfrost/gbmunge
cd gbmunge
make
cd ..
```

# Run

You will need a reference genome for your pathogen of interest. This repository includes the Respiratory Synctial Virus (RSV) genome and a small test Genbank file as an example.

Edit the config.yaml to include the path to your reference genome. This pipeline identifies the input files from the file name. If your genbank file is called "sequences.gb",
then call 

```
snakemake sequences.pb
```

and it will automatically construct the protobuf from your input data.

# Pipeline Overview

This pipeline organizes a few simple steps. 

First and optionally, it extracts a fasta and metadata from an input Genbank file using [gbmunge](https://github.com/sdwfrost/gbmunge). This step is skipped if the input is already in fasta format. Having metadata is convenient for downstream analysis, however.

Second, it aligns the fasta to the indicated reference using [ViralMSA](https://github.com/niemasd/ViralMSA) wrapping [minimap2](https://github.com/lh3/minimap2). 

Third, it converts the MSA fasta to vcf format with [faToVCF](http://hgdownload.soe.ucsc.edu/admin/exe/).

Finally, it adds the vcf to an empty tree (or a preexisting tree indicated in the config) to produce a [Mutation Annotated Tree (MAT) protobuf](https://usher-wiki.readthedocs.io/en/latest/matUtils.html#the-mutation-annotated-tree-mat-protocol-buffer-pb).

# A Note On File Sizes

While the MAT protobuf format is optimized for storage of extremely large numbers of sequences, intermediate files can become extremely large if many sequences are added all at once to the tree. It is highly recommended that the user start with a small subset of samples, perhaps a few hundred, and create an initial protobuf from that, then set the 
input_pb value in the config.yaml to the name of their initial protobuf to add additional samples in batches. 
