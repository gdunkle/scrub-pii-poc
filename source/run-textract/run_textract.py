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
        responses = []
        for sqs_records in event['Records']:
            sqs_body = json.loads(sqs_records['body'])
            for s3_records in sqs_body['Records']:
                bucket_name = s3_records['s3']['bucket']['name']
                file_key = s3_records['s3']['object']['key']
                file_name = file_key.split("/")[1]
                bucket_region = s3_records['awsRegion']

                session = boto3.session.Session(region_name=bucket_region)
                textract = session.client('textract')
                logging.info(f"Running Textract on {bucket_name}/{file_key} and posting to topic {os.environ.get('TOPIC_ARN')} with role {os.environ.get('ROLE_ARN')}")
                response = textract.start_document_text_detection(
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': bucket_name,
                            'Name': file_key
                        }
                    },
                    JobTag=file_name,
                    NotificationChannel={
                        'SNSTopicArn': os.environ.get('TOPIC_ARN'),
                        'RoleArn': os.environ.get('ROLE_ARN')
                    }
                )
                responses.append(response)
        return json.dumps(responses)
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
