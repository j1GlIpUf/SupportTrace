from app.model.clf_model import FridaClassification
import os
class ClassifierService:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        model_path = os.path.join(base_dir, "model", "my_model.joblib")
        threshold_path = os.path.join(base_dir, "model", "thresholds.json")

        self.model = FridaClassification(
        path_model=model_path,
        thresholds_path=threshold_path)

    def get_category(self, text: str) -> str:
        prediction = self.model.predict([text])
        return prediction
classifier_service = ClassifierService()

if __name__=="__main__":
    print(classifier_service.get_category("опоздала доставка"))
