#!/bin/bash
#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name solution-name version-code
#
# Paramenters:
#  - source-bucket-base-name: Name for the S3 bucket location where the template will source the Lambda
#    code from. The template will append '-[region_name]' to this bucket name.
#    For example: ./build-s3-dist.sh solutions my-solution v1.0.0
#    The template will then expect the source code to be located in the solutions-[region_name] bucket
#
#  - solution-name: name of the solution for consistency
#
#  - version-code: version of the package

# Check to see if input has been provided:
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide the base source bucket name, trademark approved solution name and version where the lambda code will eventually reside."
    echo "For example: ./build-s3-dist.sh solutions trademarked-solution-name v1.0.0"
    exit 1
fi
OVERRIDE_DEFAULT_DEPENDENCY_EXCLUDE_LIST=$4
# Get reference for all important folders
template_dir="$PWD"
template_dist_dir="$template_dir/global-s3-assets"
build_dist_dir="$template_dir/regional-s3-assets"
source_dir="$template_dir/../source"
project_dir="$template_dir/../"
site_packages=$(find $project_dir/.venv -name site-packages)
echo "------------------------------------------------------------------------------"
echo "[Init] Clean old dist, node_modules and bower_components folders"
echo "------------------------------------------------------------------------------"
echo "rm -rf $template_dist_dir"
rm -rf $template_dist_dir
echo "mkdir -p $template_dist_dir"
mkdir -p $template_dist_dir
echo "rm -rf $build_dist_dir"
rm -rf $build_dist_dir
echo "mkdir -p $build_dist_dir"
mkdir -p $build_dist_dir

echo "------------------------------------------------------------------------------"
echo "[Packing] Templates"
echo "------------------------------------------------------------------------------"
cp $template_dir/*.template $template_dist_dir/
echo "copy yaml templates and rename"
cp $template_dir/*.yaml $template_dist_dir/
cd $template_dist_dir
# Rename all *.yaml to *.template
for f in *.yaml; do 
    mv -- "$f" "${f%.yaml}.template"
done
timestamp="$(date +"%Y-%m-%d-%H%M%S")"
ZIP_FILE_NAME="run-textract-$timestamp.zip"
LAYER_FILE_NAME="run-textract-layer-$timestamp.zip"
cd ..
echo "Updating code source bucket in template with $1"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template
replace="s/%%SOLUTION_NAME%%/$2/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template
replace="s/%%VERSION%%/$3/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template

replace="s/%%TIMESTAMP%%/$timestamp/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template

replace="s/%%ZIP_FILE_NAME%%/$ZIP_FILE_NAME/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template

replace="s/%%LAYER_FILE_NAME%%/$LAYER_FILE_NAME/g"
echo "sed -i '' -e $replace $template_dist_dir/*.template"
sed -i '' -e $replace $template_dist_dir/*.template

echo "------------------------------------------------------------------------------"
echo "[Build] Run Textract Function"
echo "------------------------------------------------------------------------------"
cd $source_dir/run-textract
zip $build_dist_dir/$ZIP_FILE_NAME ./*.py

#MoveDocumentsFunction_Sha256=$(shasum -a 256 -b $build_dist_dir/$ZIP_FILE_NAME | tr -s ' ' | cut -d ' ' -f 1)
#replace="s/%%MoveDocumentsFunction_Sha256%%/$MoveDocumentsFunction_Sha256/g"
#echo "sed -i '' -e $replace $template_dist_dir/*.template"
#sed -i '' -e $replace $template_dist_dir/*.template

echo "------------------------------------------------------------------------------"
echo "[Build] Depending Layer"
echo "------------------------------------------------------------------------------"

DEPENDENCY_EXCLUDE_LIST=${OVERRIDE_DEFAULT_DEPENDENCY_EXCLUDE_LIST:=["aws_cdk","boto3","dist-info","pip","botocore","jsii","docutils","pkg_resources","setuptools","test","tests","s3transfer"]}
echo "Excluding dependencies: $DEPENDENCY_EXCLUDE_LIST"
dependencies=$(jq -r --arg blacklist $DEPENDENCY_EXCLUDE_LIST  ' .default | to_entries[] | .key | select(. as $in | $blacklist | index($in) | not) '  $project_dir/Pipfile.lock)
rm -Rf $build_dist_dir/python
mkdir $build_dist_dir/python

for k in $dependencies
do
  find $site_packages -name ${k/-/_} -type d -exec cp -r {}  $build_dist_dir/python/ \;
  find $site_packages -name $k'-*.dist-info' -type d -exec cp -r {}  $build_dist_dir/python/ \;
done
cd $build_dist_dir
zip -r $build_dist_dir/$LAYER_FILE_NAME ./python
rm -Rf ./python
# cp ./dist/example-function-js.zip $build_dist_dir/example-function-js.zip
