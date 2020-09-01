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
        textract_notification_msg=json.loads(event["Records"][0]["Sns"]["Message"])
        status=textract_notification_msg["Status"]
        job_id=textract_notification_msg["JobId"]
        original_file_name = textract_notification_msg["DocumentLocation"]["S3ObjectName"]
        if status=="SUCCEEDED":
            
            input = {
                "job_id":job_id,
                "next_token": None,
                "continue": "true",
                "document": None,
                "file_name": original_file_name
            }
            step_functions = boto3.client('stepfunctions')
            step_function_arn = str(os.environ.get('STEP_FUNCTION'))
            step_function_execution_result=step_functions.start_execution(stateMachineArn=step_function_arn,name=job_id,input=json.dumps(input))
            result = {
                'statusCode': '200',
                'body':  {'status': status,"job_id":job_id,"step_function": step_function_execution_result}
            }
        else:
             result = {
                'statusCode': '500',
                'body':  {'status': status,"job_id":job_id}
            }
        logging.info("Result: %s" % result)
        return result
    except Exception as error:
        logging.error('lambda_handler error: %s' % (error))
        logging.error('lambda_handler trace: %s' % traceback.format_exc())
        result = {
            'statusCode': '500',
            'body':  {'message': 'error'}
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