from transformers import pipeline

classifier = pipeline(
    "sentiment-analysis",
    model="ProsusAI/finbert"
)

# headline = "Apple stock surges after strong earnings report"

# result = classifier(headline)

# print(result)

def sentiment(classifier,headlines):

    result = []
    for headline in headlines:
        prediction = classifier(headline)[0]

        result.append(prediction) 
    
    return result    