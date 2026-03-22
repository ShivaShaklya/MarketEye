import json
import os

data_path="data/processed_youtube/smartphones"

#print product names where feature sentiment is negative
for file in os.listdir(data_path):
    file_path=os.path.join(data_path,file)
    with open(file_path,"r", encoding="utf-8") as f:
        data=json.load(f)
    product=data["product"]
    for feature_data in data["features"]:
        if feature_data["sentiment"]=="negative":
            print(f"Product: {product}, Feature: {feature_data['feature']}")