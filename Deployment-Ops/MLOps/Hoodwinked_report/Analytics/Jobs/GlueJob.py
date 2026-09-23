import boto3
from django.conf import settings
import os

class GlueJob:
    @staticmethod
    def trigger_glue_job(input_file_name):

        job_name = 'trade'
        bucket_name = settings.AWS_STORAGE_BUCKET
        region = settings.AWS_REGION

        glue = boto3.client('glue', region_name=region)
        
        file_name, file_extension = os.path.splitext(input_file_name)
        
        output_file_name = f"{file_name}_processed{file_extension}"
        
        response = glue.start_job_run(
            JobName=job_name,
            Arguments={
                '--INPUT_FILE': input_file_name,
                '--BUCKET_NAME': bucket_name,
                '--OUTPUT_PATH': output_file_name
            }
        )
        
        job_run_id = response['JobRunId']
        return job_run_id

