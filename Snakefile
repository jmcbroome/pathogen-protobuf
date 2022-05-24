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
        python3 ViralMSA.py -s {input} -r {config[reference]} -e none -o tmp
        mv tmp/{sample}.fasta.aln .
        rm -r tmp
        """

rule fatovcf:
    input:
        "{sample}.fasta.aln"
    output:
        "{sample}.vcf"
    shell:
        "{config[fatovcf]} {input} {output}"

if len(config["input_pb"]) > 0:
    rule expand_tree:
        input:
            "{sample}.vcf"
        output:
            "{sample}.pb"
        shell:
            "usher -t seed.nwk -v {input} -o {output}"
else:
    rule build_tree:
        input:
            "{sample}.vcf"
        output:
            "{sample}.pb"
        shell:
            "usher -i {config[input_pb]} -v {input} -o {output}"

