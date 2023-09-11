from flask import abort, jsonify
from collections import OrderedDict
from app import common

#URL = 'http://127.0.0.1:5000/subject-operations/genotype-operations/$find-subject-variants?subject=HG00403&ranges=NC_000019.9:11200138-11244496&includeVariants=true&includePhasing=false'
def find_subject_variants(
        subject, ranges, testIdentifiers=None, testDateRange=None,
        specimenIdentifiers=None, genomicSourceClass=None,
        includeVariants=True, includePhasing=False):

    # Parameters
    subject = subject.strip()
    common.validate_subject(subject)

    ranges = list(map(common.get_range, ranges))

    # Query
    query = {}

    # date query
    if testDateRange:
        testDateRange = list(map(common.get_date, testDateRange))
        query["testDate"] = {}

        for date_range in testDateRange:
            query["testDate"][date_range['OPERATOR']] = date_range['DATE']

    # Subject Query
    query["patientID"] = {"$eq": subject}

    # testIdentifiers query
    if testIdentifiers:
        testIdentifiers = list(map(str.strip, testIdentifiers))
        query["testID"] = {"$in": testIdentifiers}

    # specimenIdentifiers query
    if specimenIdentifiers:
        specimenIdentifiers = list(map(str.strip, specimenIdentifiers))
        query["specimenID"] = {"$in": specimenIdentifiers}

    # Genomic Source Class Query
    if genomicSourceClass:
        genomicSourceClass = genomicSourceClass.strip().lower()
        query["genomicSourceClass"] = {"$eq": genomicSourceClass}

    # Genomics Build Presence
    genomics_build_presence = common.get_genomics_build_presence(query)

    # Chromosome To Ranges
    chromosome_to_ranges = common.get_chromosome_to_ranges(ranges, genomics_build_presence)

    # Result Object
    result = OrderedDict()
    result["resourceType"] = "Parameters"
    result["parameter"] = []

    # For each chromosome-range pair query the database for "variants" and
    # create a Parameters FHIR Object.
    for chrom in chromosome_to_ranges:
        parameter = OrderedDict()

        parameter["name"] = "variants"
        parameter["part"] = []
        parameter["part"].append({
            "name": "rangeItem",
            "valueString": f'{chrom["RefSeq"]}:{chrom["PGB"]["L"]}-{chrom["PGB"]["H"]}'
        })

        variant_q = []
        genomic_builds = [chrom["PGB"]["BUILD"]]

        query["$and"] = []
        query["$and"].append({"SVTYPE": {"$exists": False}})
        query["$and"].append({"$expr": {"$gte": [{"$subtract": [{"$add": [{"$strLenCP": "$REF"}, "$POS"]}, "$POS"]}, 1]}})
        query["$and"].append({"$or": [
            {
                "$and": [
                    {"POS": {"$lte": chrom["PGB"]["L"]}},
                    {"$expr": {"$gt": [{"$add": [{"$strLenCP": "$REF"}, "$POS"]}, chrom["PGB"]["L"]]}}
                ]
            },
            {
                "$and": [
                    {"POS": {"$gte": chrom["PGB"]["L"]}},
                    {"POS": {"$lt": chrom["PGB"]["H"]}}
                ]
            }
        ]})
        query["$and"].append({"CHROM": {"$eq": chrom["CHROM"]}})

        if chrom["OGB"] is not None:
            query["$and"][2]["$or"].extend(
                [{
                    "$and": [
                        {"POS": {"$lte": chrom["OGB"]["L"]}},
                        {"$expr": {"$gt": [{"$add": [{"$strLenCP": "$REF"}, "$POS"]}, chrom["OGB"]["L"]]}}
                    ]
                },
                    {
                    "$and": [
                        {"POS": {"$gte": chrom["OGB"]["L"]}},
                        {"POS": {"$lt": chrom["OGB"]["H"]}}
                    ]
                }]
            )

            genomic_builds.append(chrom["OGB"]["BUILD"])

        query["genomicBuild"] = {"$in": genomic_builds}

        try:
            variant_q = common.variants_db.aggregate([{"$match": query}])
            variant_q = list(variant_q)
        except Exception as e:
            print(f"DEBUG: Error{e} under find_subject_variants query={query}")
            variant_q = []

        # Variants
        present = bool(variant_q)

        parameter["part"].append({
            "name": "presence",
            "valueBoolean": present
        })

        if present:
            if includeVariants:
                variant_fhir_profiles = []

                for record in variant_q:
                    ref_seq = common.get_ref_seq_by_chrom_and_build(record['genomicBuild'], record['CHROM'])
                    resource = common.create_fhir_variant_resource(record, ref_seq, subject)

                    variant_fhir_profiles.append(resource)

                if variant_fhir_profiles:
                    variant_fhir_profiles = sorted(variant_fhir_profiles, key=lambda d: d['id'])

                for resource in variant_fhir_profiles:
                    parameter["part"].append({
                        "name": "variant",
                        "resource": resource
                    })

                if includePhasing:
                    variantIDs = [str(v['_id']) for v in variant_q]
                    sequence_phase_profiles = []
                    sequence_phase_data = common.get_sequence_phase_data(
                        subject)

                    for sq_data in sequence_phase_data:
                        if sq_data["variantID1"] in variantIDs and sq_data["variantID2"] in variantIDs:
                            sq_profile = common.create_sequence_phase_relationship(subject, sq_data)

                            sequence_phase_profiles.append(sq_profile)

                    if sequence_phase_profiles:
                        sequence_phase_profiles = sorted(sequence_phase_profiles, key=lambda d: d['id'])

                    for sq_profile in sequence_phase_profiles:
                        parameter["part"].append({
                            "name": "sequencePhaseRelationship",
                            "resource": sq_profile
                        })

        result["parameter"].append(parameter)

    if not result["parameter"]:
        result.pop("parameter")

    return jsonify(result)