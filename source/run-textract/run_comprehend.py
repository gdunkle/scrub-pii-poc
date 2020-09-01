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


def lambda_handler(event, context):
    try:
        logging.debug(event)
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
        file_key_path = file_key.split("/")
        textract_job_id = file_key_path[0]
        bucket_region = event['Records'][0]['awsRegion']

        session = boto3.session.Session(region_name=bucket_region)

        comprehend_medical = session.client('comprehendmedical')
        s3 = session.client("s3")
        head_response = s3.head_object(Bucket=bucket_name, Key=file_key)
        original_file_name = head_response["Metadata"]["x-amz-meta-original-file-name"] if "Metadata" in head_response and "x-amz-meta-original-file-name" in head_response["Metadata"] else "default.txt"

        logging.info("original_file_name: %s" % original_file_name)
        logging.debug("Input: %s" % {
            'S3Bucket': bucket_name,
            'S3Key': file_key_path[0]
        })
        logging.debug("Output: %s" % {
            'S3Bucket': os.environ.get('DESTINATION_BUCKET'),
            'S3Key': f"{textract_job_id}/{original_file_name}"
        })
        response = comprehend_medical.start_phi_detection_job(
            InputDataConfig={
                'S3Bucket': bucket_name,
                'S3Key': file_key_path[0]
            },
            OutputDataConfig={
                'S3Bucket': os.environ.get('DESTINATION_BUCKET'),
                'S3Key': f"{textract_job_id}/{original_file_name}"
            },
            DataAccessRoleArn=os.environ.get('DATA_ACCESS_ROLE'),
            LanguageCode="en",
            JobName=original_file_name
        )
        step_function_input = {
            "original_file_name": original_file_name,
            "textract": {
                "job_id": file_key_path[0],
                "bucket": bucket_name,
                "object_key": file_key
            },
            "comprehend_medical": {
                "JobId": response["JobId"],
                "JobStatus": "SUBMITTED"

            }
        }
        step_functions = boto3.client('stepfunctions')
        step_function_arn = str(os.environ.get('STEP_FUNCTION'))
        step_function_execution_result = step_functions.start_execution(stateMachineArn=step_function_arn,
                                                                        name=response["JobId"],
                                                                        input=json.dumps(step_function_input))
        result = {
            'step_function_execution_result': step_function_execution_result,
            'step_function_input': step_function_input
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
