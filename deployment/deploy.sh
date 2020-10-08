#!/bin/bash

export SOLUTION_NAME=scrub-pii-poc
export DIST_OUTPUT_BUCKET=awsgalen-solutions
export VERSION=1.0.0
export AWS_REGION=us-east-2
echo $SOLUTION_NAME 
echo $DIST_OUTPUT_BUCKET
echo $VERSION
echo $AWS_REGION
DEPENDENCY_EXCLUDE_LIST=["aws_cdk","dist-info","pip","jsii","docutils","pkg_resources","setuptools","test","tests","s3transfer"]
./build-s3-dist.sh $DIST_OUTPUT_BUCKET $SOLUTION_NAME $VERSION $DEPENDENCY_EXCLUDE_LIST
aws s3 cp ./regional-s3-assets/ s3://$DIST_OUTPUT_BUCKET-$AWS_REGION/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control

echo "Deploying stack $SOLUTION_NAME"
echo "aws cloudformation deploy  --stack-name $SOLUTION_NAME --s3-bucket $DIST_OUTPUT_BUCKET-$AWS_REGION --s3-prefix $SOLUTION_NAME/$VERSION --template-file ./global-s3-assets/environment.template  --capabilities CAPABILITY_IAM"
aws cloudformation deploy --region $AWS_REGION  --stack-name $SOLUTION_NAME --s3-bucket $DIST_OUTPUT_BUCKET-$AWS_REGION --s3-prefix $SOLUTION_NAME/$VERSION --template-file ./global-s3-assets/environment.template  --capabilities CAPABILITY_IAM
    

