from kafka import KafkaConsumer
import time
import boto3
import json
import ray

class PreProcessing:
    def __init__(self, topic_name, bootstrap_servers, group_id, batch_size, batch_timeout,endpoint,region):
        self.topic_name = topic_name
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.endpoint_name = endpoint
        self.region_name = region
        self.batches = []
        self.outputs = [] # Stores the input along with the corresponding output
        ray.init()

    # Initializes the Kafka Consumer 
    def initialiseConsumer(self):
        consumer = KafkaConsumer(self.topic_name,
                                 bootstrap_servers=self.bootstrap_servers)
                                #  group_id=self.group_id)
        return consumer
    # Divides the complete stream of data into batches 
    def process_batch(self):
        consumer = self.initialiseConsumer()
        tmpBatch = []
        batch_st = time.time()
        try:
            for message in consumer:
                tmpBatch.append(message.value)
                if len(tmpBatch) >= self.batch_size or (time.time() - batch_st) >= self.batch_timeout:
                    self.batches.append(tmpBatch)

                    # Uncomment if model endpoint is configured

                    # output = self.parallelInvoke(tmpBatch)                        # Once a Batch is made, it is passed to the aws sagemaker endpoint and the output is maintained in the output variable
                    # self.outputs.append(output)

                    print(tmpBatch)
                    tmpBatch = []
                    batch_st = time.time()
        except Exception as e:
            return f"Error: {e}"
        
        # The block below is commented out, to enable batches to be continuosly formed for the entire stream

        # finally:
        #     if tmpBatch:
        #         self.batches.append(tmpBatch)
        #     consumer.close()
        #     return self.outputs
        # Takes in only a single batch and passes it to the model

    def model(self, batch):
        sagemaker_runtime = boto3.client("sagemaker-runtime", region_name=self.region_name)
        payload = json.dumps(batch)
        try:
            response = sagemaker_runtime.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType="application/json",
                Body=payload
            )
            return [{"Payload":payload},{"Response":response}]   
        except Exception as e:
            return f"Error: {e}"  
    @ray.remote
    def parallelInvoke(self, batch):
        return self.model(batch)  

# class invokeMLModel:
#     def __init__(self, endpoint, region, cumulativeBatches):
#         self.endpoint_name = endpoint
#         self.region_name = region
#         self.cumulativeBatches = cumulativeBatches  # Cumulative Batches Data

#         # Initializing Parallel Processing
#         ray.init()

#     # Takes in only a single batch and passes it to the model
#     def model(self, batch):
#         sagemaker_runtime = boto3.client("sagemaker-runtime", region_name=self.region_name)
#         payload = json.dumps(batch)
#         try:
#             response = sagemaker_runtime.invoke_endpoint(
#                 EndpointName=self.endpoint_name,
#                 ContentType="application/json",
#                 Body=payload
#             )
#             return [{"Payload":payload},{"Response":response}]
#         except Exception as e:
#             return f"Error: {e}"
#     @ray.remote
#     def parallelInvoke(self, batch):
#         return self.model(batch)
    
#     # For executing all the endpoint invocations in parallel for all batches
#     def executeResults(self):
#         cumulativeResults = [self.parallelInvoke.remote(batch) for batch in self.batches ]
#         compiledResults = ray.get(cumulativeResults)
#         return compiledResults
