#!/bin/bash

# Fetch all available AWS regions
regions=$(aws ec2 describe-regions --query "Regions[].RegionName" --output text)

echo "Listing all SageMaker Endpoints and their instance types across all regions..."

for region in $regions; do
  echo "Region: $region"
  
#   # List all SageMaker endpoints in the current region
#   endpoints=$(aws sagemaker list-endpoints --region "$region" --query 'Endpoints[*].EndpointName' --output text)

#   if [ -z "$endpoints" ]; then
#     echo "No SageMaker endpoints found in region $region"
#   else
#     for endpoint in $endpoints; do
#       # Fetch the endpoint configuration for each endpoint
#       config_name=$(aws sagemaker describe-endpoint --endpoint-name "$endpoint" --region "$region" --query 'EndpointConfigName' --output text)
      
#       # Fetch instance types and instance count used in the endpoint configuration
#       aws sagemaker describe-endpoint-config --endpoint-config-name "$config_name" --region "$region" \
#         --query 'ProductionVariants[*].[InstanceType, InitialInstanceCount]' --output table \
#         | awk -v endpoint="$endpoint" '{print "Endpoint:", endpoint, "|", $0}'
#     done
#   fi

  echo "---------------------------------------------"
done
