configfile: "config.yaml"

rule all:
    input:
        "{sample}.pb"

rule munge:
    input:
        "{sample}.gb"
    output:
        "{sample}.fasta",
        "{sample}_metadata.tsv"
    shell:
        "{config[gbmunge]} -i {input} -f {output[0]} -o {output[1]}"

rule msa:
    input:
        "{sample}.fasta"
    output:
        "{sample}.fasta.aln"
    shell:
        """
        python3 ViralMSA/ViralMSA.py -s {input} -r {config[reference]} -e none -o ./tmp -a minimap2
        mv tmp/* .
        rm -r tmp
        """

rule merge:
    input:
        "{sample}.fasta.aln"
    output:
        "{sample}.merged.fasta.aln"
    shell:
        "cat {config[reference]} {input} > {output}"

rule fatovcf:
    input:
        "{sample}.merged.fasta.aln"
    output:
        "{sample}.vcf"
    shell:
        "{config[fatovcf]} {input} {output}"

if config["input_pb"] != None:
    rule expand_tree:
        input:
            "{sample}.vcf"
        output:
            "{sample}.pb"
        shell:
            "{config[usher_cmd]} -i {config[input_pb]} -v {input} -o {output}"
else:
    rule build_tree:
        input:
            "{sample}.vcf"
        output:
            "{sample}.pb"
        shell:
            "{config[usher_cmd]} -t seed.nwk -v {input} -o {output}"
