#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
#                                                                            #
#  Licensed under the Amazon Software License (the "License"). You may not   #
#  use this file except in compliance with the License. A copy of the        #
#  License is located at                                                     #
#                                                                            #
#      http://aws.amazon.com/asl/                                            #
#                                                                            #
#  or in the "license" file accompanying this file. This file is distributed #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,        #
#  express or implied. See the License for the specific language governing   #
#  permissions and limitations under the License.                            #
##############################################################################

import logging
import json
import os
import traceback
import sys
import boto3
from botocore.config import Config


def lambda_handler(event, context):
    try:
        logging.debug(event)
        config = Config(
            retries={
                'max_attempts': 10,
                'mode': 'standard'
            }
        )
        comprehend = boto3.client('comprehend', config=config)
        textract = boto3.client('textract', config=config)

        s3 = boto3.client('s3')
        logging.debug(event)

        job_id = event["job_id"]
        next_token = event["next_token"]
        proceed = event["continue"]
        document = event["document"]
        file_name = event["file_name"]
        input = {
            "JobId": job_id,
            "MaxResults": 100
        }
        if next_token is not None:
            input["NextToken"] = next_token
        response = text_detection_results = textract.get_document_text_detection(**input)
        blocks = response["Blocks"]
        processed_blocks = [x for x in [get_block_value(block) for block in blocks] if x is not None]
        units = group_blocks_into_units(processed_blocks, 0)
        scrubbed_data = [scrub_data(unit, comprehend) for unit in units]
        logging.debug(scrubbed_data)

        text = append_results_to_working_document_text(document, scrubbed_data, s3)
        if document is None:
            document = {
                "Bucket": str(os.environ.get('WORKING_BUCKET')),
                "Key": job_id
            }
        if text is not None:
            logging.debug(text)
            write_text_to_s3(document, text, s3)
        next_token = response["NextToken"] if "NextToken" in response else None
        result = {
            "job_id": job_id,
            "next_token": next_token,
            "continue": next_token is not None,
            "document": document,
            "file_name": file_name
        }
        logging.info("Result: %s" % result)
        return result
    except Exception as error:
        logging.error('lambda_handler error: %s' % (error))
        logging.error('lambda_handler trace: %s' % traceback.format_exc())
        result = {
            'statusCode': '500',
            'body': {'message': 'error'}
        }
        return json.dumps(result)


def append_results_to_working_document_text(document, new_results, s3):
    result = None
    if document is not None and new_results is not None:
        obj = s3.get_object(Bucket=document["Bucket"], Key=document["Key"])
        text = obj['Body'].read().decode('utf-8')
        result = text + "\n" + ("\n".join(new_results))
    elif new_results is not None:
        result = "\n".join(new_results)
    return result


def write_text_to_s3(document, text, s3):
    s3.put_object(Body=text, Bucket=document["Bucket"], Key=document["Key"])


def get_block_value(block: dict) -> str:
    block_type = block["BlockType"]
    return block["Text"] if block_type in ["LINE"] else None


def scrub_data(unit, comprehend):
    response = comprehend.detect_pii_entities(Text=unit, LanguageCode='en')
    if len(response["Entities"]) > 0:
        phi_values_to_replace = {}
        for entity in response["Entities"]:
            if entity["Type"] in phi_values_to_replace:
                phi_values_to_replace[entity["Type"]].append(unit[entity["BeginOffset"]:entity["EndOffset"]])
            else:
                phi_values_to_replace[entity["Type"]] = [unit[entity["BeginOffset"]:entity["EndOffset"]]]

        unit = replace_phi_values(unit, phi_values_to_replace)
    else:
        logging.debug("No PII data found in '%s'" % unit)
    return unit


def replace_phi_values(in_string: str, phi_values_to_replace: dict) -> str:
    for key, value in phi_values_to_replace.items():
        in_string = replace_phi_values_of_type(in_string, key, value)
    return in_string


def replace_phi_values_of_type(in_string: str, type: str, values) -> str:
    for value in sorted(values, key=len, reverse=True):
        in_string = in_string.replace(value, "<%s>" % type)
    return in_string


def group_blocks_into_units(processed_blocks, index):
    unit_str = ""
    results = []
    logging.debug(f"group_blocks_into_units.processed_blocks {processed_blocks},{index}")
    if processed_blocks is not None and len(processed_blocks) > 0:
        for i in range(index, len(processed_blocks)):
            block = processed_blocks[i]
            unit_str = block if len(unit_str) == 0 else "%s\n%s" % (unit_str, block)
            if len(unit_str) > 5000:
                results.append(unit_str)
                unit_str = ""
                break
        if unit_str != "":
            results.append(unit_str)
        if (i + 1) < len(processed_blocks):
            results = results + group_blocks_into_units(processed_blocks, i + 1)
    return results


def init_logger():
    global log_level
    log_level = str(os.environ.get('LOG_LEVEL')).upper()
    if log_level not in [
        'DEBUG', 'INFO',
        'WARNING', 'ERROR',
        'CRITICAL'
    ]:
        log_level = 'ERROR'
    logging.getLogger().setLevel(log_level)


init_logger()
