# TODO: Test the code by inputting real data and the sagemaker endpoint

# Initialising the Kafka variables -> from Quantbot RedPandas Pipeline
TOPIC_NAME = "real-time-data"
BOOTSTRAP_SERVERS = ["localhost:9092"]
GROUP_ID = "enter_group_id"
BATCH_SIZE = 1000  # TODO: Decide on the number of messages per batch
BATCH_TIMEOUT = 5 # TODO: Decide on the number of seconds of wait before sending a batch


#aws config
# Configuration
endpoint_name = 'your-endpoint-name'  # Replace with your SageMaker endpoint name
region = 'us-west-2'  # Replace with your AWS region


from preProcessScript import PreProcessing


def main():
    init = PreProcessing(TOPIC_NAME,BOOTSTRAP_SERVERS,GROUP_ID,BATCH_SIZE,BATCH_TIMEOUT,endpoint_name,region)
    execModel = init.process_batch()
    print(execModel.outputs)
    # Model = invokeMLModel(endpoint_name,region,batches)
    # outputs = Model.executeResults()
    # return outputs
if __name__ == "__main__":
    main()