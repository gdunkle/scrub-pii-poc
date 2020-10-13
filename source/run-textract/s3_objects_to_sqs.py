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

config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'standard'
    }
)
s3_client = boto3.client("s3", config=config)
sqs_client = boto3.client("sqs", config=config)
SQS_QUEUE_URL = str(os.environ.get('SQS_QUEUE_URL'))
S3_MAX_KEYS = int(os.environ.get('S3_MAX_KEYS'))
SQS_MAX_RECORDS_LENGTH = int(os.environ.get('SQS_MAX_RECORDS_LENGTH'))


##
# input:
#
#
#
##
def lambda_handler(event, context):
    logging.debug(event)
    bucket = event["bucket"]
    region = event["region"]
    args = {
        "Bucket": bucket

    }
    count = event["count"] if "count" in event.keys() else 0
    prefix = event["prefix"] if "prefix" in event.keys() else None
    if prefix is not None:
        args["Prefix"] = prefix
    continuation_token = event.pop("NextContinuationToken",None)
    if continuation_token is not None:
        args["ContinuationToken"] = continuation_token
    list_objects_response = s3_client.list_objects_v2(**args)
    results = create_s3_records()
    for s3_object in list_objects_response["Contents"]:
        if s3_object["Size"] > 0:
            fake_s3_event = create_s3_event(s3_object["Key"], bucket, region)
            count += 1
            results["Records"].append(fake_s3_event)
            if len(results["Records"]) == SQS_MAX_RECORDS_LENGTH:
                sqs_client.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(results))
                results = create_s3_records()
        else:
            logging.warning(f"Skipping {s3_object['Key']} because it's size is zero")
    if len(results["Records"]) > 0:
        sqs_client.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(results))
    if "NextContinuationToken" in list_objects_response.keys():
        event["NextContinuationToken"] = list_objects_response["NextContinuationToken"]
    event["count"] = count
    return json.dumps(event)


def create_s3_event(key: str, bucket: str, region: str) -> dict:
    return {
        "awsRegion": region,
        "s3": {
            "bucket": {
                "name": bucket
            },
            "object": {
                "key": key
            }
        }
    }


def create_s3_records() -> dict:
    return {
        "Records": []
    }


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
