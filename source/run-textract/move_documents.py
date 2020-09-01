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
        s3 = boto3.client('s3')
        logging.debug(event)
        job_id = event["job_id"]
        tmp_document = event["document"]
        file_name = event["file_name"]
        destination_document = {
            "Bucket": str(os.environ.get('DESTINATION_BUCKET')),
            "Key": f"{job_id}/extracted.txt"
        }
        response = s3.copy_object(Bucket=destination_document["Bucket"], Key=destination_document["Key"],
                                  CopySource=tmp_document, Metadata={
                'x-amz-meta-original-file-name': file_name
            }, MetadataDirective="REPLACE")
        logging.info(response)
        logging.info("Deleting tmp document %s" % tmp_document)
        s3.delete_object(Bucket=tmp_document["Bucket"],Key=tmp_document["Key"])
        result = {
            "from": tmp_document,
            "to": destination_document
        }
        return result
    except Exception as error:
        logging.error('lambda_handler error: %s' % (error))
        logging.error('lambda_handler trace: %s' % traceback.format_exc())
        result = {
            'statusCode': '500',
            'body':  {'message': 'error'}
        }
        return json.dumps(result)
        


def group_blocks_into_units(processed_blocks,index):
    unit_str=""
    results=[]
    for i in range(index,len(processed_blocks)):
        block=processed_blocks[i]
        unit_str = block if len(unit_str)==0 else "%s %s" % (unit_str,block)
        if len(unit_str)>=100:
            results.append(unit_str)
            unit_str=""
            break
    if unit_str != "":
        results.append(unit_str)
    if (i+1) < len(processed_blocks):
        results=results+group_blocks_into_units(processed_blocks,i+1)
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
