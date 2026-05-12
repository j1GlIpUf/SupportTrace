from sentence_transformers import SentenceTransformer
import joblib
import json
import numpy as np
from typing import List


class FridaClassification:
    def __init__(self,path_model:str,thresholds_path:str):
        
        self.model:object=joblib.load(path_model)

        self.encoder:object=SentenceTransformer("ai-forever/FRIDA")

        with open(thresholds_path,"r") as f:
            self.thrashold:List=json.load(f)

    def predict_proba(self,texts:List[str])->np.ndarray:

        texts_enc=self.encoder.encode(texts)
        proba=self.model.predict_proba(texts_enc)

        return proba

        
    def predict(self,texts:List[str])->np.array:

        proba=self.predict_proba(texts)

        y_pred_thresh = np.zeros_like(proba)

        for i, th in enumerate(self.thrashold):
            y_pred_thresh[i][:,1] = (proba[i][:, 1] >= th).astype(int)

        predict=np.array([y_pred_thresh[:,i,1] for i in range(len(texts))])
        return predict




"""if __name__ == "__main__":
    model = FridaClassification(
        path_model="my_model.joblib",
        thresholds_path="thresholds.json"
    )
    print(model.predict(["Доставка опоздала"]))
"""