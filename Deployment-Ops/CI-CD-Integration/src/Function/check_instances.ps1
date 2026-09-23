# Define AWS region and preferred instance types
$Region = "us-east-1"
$PreferredInstanceTypes = @(
    # GPU-based (Moderate cost and performance)
    "ml.g4dn.xlarge",
    "ml.g4dn.2xlarge",
    "ml.g4dn.4xlarge",
    "ml.g4dn.8xlarge",
    "ml.g4dn.12xlarge",

    # Older generation GPU-based
    "ml.p2.xlarge",
    "ml.p2.8xlarge",
    "ml.p2.16xlarge",

    # Newer generation high-performance GPU
    "ml.g5.xlarge",
    "ml.g5.2xlarge",

    # CPU-based (General purpose)
    "ml.m5.large",
    "ml.m5.xlarge",
    "ml.m5.2xlarge",
    "ml.m5.4xlarge",
    "ml.m5.12xlarge",

    # Older generation CPU-based
    "ml.m4.large",
    "ml.m4.xlarge",
    "ml.m4.2xlarge",
    "ml.m4.4xlarge",

    # Compute-optimized CPU
    "ml.c5.large",
    "ml.c5.xlarge",
    "ml.c5.2xlarge",
    "ml.c5.4xlarge",
    "ml.c5.9xlarge",

    # Memory-optimized CPU
    "ml.r5.large",
    "ml.r5.xlarge",
    "ml.r5.2xlarge",
    "ml.r5.4xlarge",

    # Cost-effective instances
    "ml.t3.medium",
    "ml.t3.large",
    "ml.t2.medium",
    "ml.t2.large"
)

# Retrieve available SageMaker instance types in the specified region
$AvailableInstanceTypes = aws ec2 describe-instance-type-offerings `
    --location-type availability-zone `
    --filters Name=instance-type,Values=ml.* `
    --region $Region `
    --output text --query "InstanceTypeOfferings[].InstanceType"

# Convert available instance types to an array for easy comparison
$AvailableInstanceTypesArray = $AvailableInstanceTypes -split "\s+"

# Output the available instance types
Write-Output "Available instance types in region ${Region}: ${AvailableInstanceTypesArray}"

# Initialize variable to store the selected instance type
$SelectedInstanceType = $null

# Check if there are available instance types
if ($AvailableInstanceTypesArray.Count -eq 0) {
    Write-Output "No SageMaker-compatible instance types are available in this region."
} else {
    # Loop through each preferred instance type and select the first available one
    foreach ($instance in $PreferredInstanceTypes) {
        if ($AvailableInstanceTypesArray -contains $instance) {
            $SelectedInstanceType = $instance
            Write-Output "Selected instance type: $SelectedInstanceType"
            break
        }
    }

    # If no preferred instance type is available, output a message
    if (-not $SelectedInstanceType) {
        Write-Output "None of the preferred instance types are available in this region."
    }
}
