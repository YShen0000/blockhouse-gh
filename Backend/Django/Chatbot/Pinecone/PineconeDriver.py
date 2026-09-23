import hashlib
from pinecone import Pinecone, PodSpec
from sentence_transformers import SentenceTransformer


class PineconeDriver:
    def __init__(
        self,
        api_key,
        index_name,
        environment,
        model_name="all-MiniLM-L6-v2",
        vector_dimension=384,
    ):
        self.api_key = api_key
        self.index_name = index_name
        self.environment = environment
        self.vector_dimension = vector_dimension
        self.model = SentenceTransformer(model_name)

        # pinecone.init(api_key=self.api_key, environment=self.environment)

        pc = Pinecone(api_key=self.api_key, environment=self.environment)

        # Upgrade to use below code!!
        # if self.index_name not in pc.list_indexes():
        #     pc.create_index(
        #         name=self.index_name,
        #         dimension=self.vector_dimension,
        #         spec=PodSpec(
        #             environment="us-east1-gcp",
        #             pod_type="p1.x1",
        #             pods=1
        #         ))
        self.index = pc.Index(self.index_name)

    def generate_id(self, text, times):
        """
        Generate a unique ID based on text, start time, and end time.
        """
        id_string = f"{text}_{times[0]}_{times[1]}"
        return hashlib.sha256(id_string.encode()).hexdigest()

    def store_data(self, texts, times):
        """
        Store text data along with start and end times in the Pinecone index.
        """
        for text, time in zip(texts, times):
            unique_id = self.generate_id(text, time)
            # Convert ndarray to list
            vector = self.model.encode([text])[0].tolist()
            metadata = {"description": text,
                        "start_time": time[0], "end_time": time[1]}
            self.index.upsert(vectors=[(unique_id, vector, metadata)])

    def query(self, query_text, top_k=5):
        """
        Perform a semantic search on the stored data.
        :param query_text: The text query for the search.
        :param top_k: Number of top results to return.
        :return: Search results.
        """
        query_vector = self.model.encode([query_text]).tolist()
        return self.index.query(vector=query_vector, include_metadata=True, top_k=top_k)
