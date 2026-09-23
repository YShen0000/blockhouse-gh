 # 1. Required Data
 - 1. Timestamp and ticker of the corresponding news
 - 2. News content: str type
 - 3. Weight: The tag of the news. We will convert tag to weights, like putting more weight on financial statement or breaking news.

 # 2. Principle of the Feature
 - 1. We use model FinancialBERT on hugging face to detect the sentiment of a news. The result would be 1(positive), 0(neutral), and -1(negative).
 - 2. Sometimes, we will have multiple news at the same minutes. Therefore, we will calculate their weighted average.

 # 3. Another model plan
 - We only calculate the sentiment of those news with a tag 'Major Events', so that we can better predict high volatility.

 # 4. Relative Link
 1. Data Requirement
 https://www.notion.so/blockhouse1/Data-Requirements-127ca1a7e5b480f7be6ed385044d9e18
 2. Link of FinancialBERT model
 https://huggingface.co/ahmedrachid/FinancialBERT-Sentiment-Analysis
