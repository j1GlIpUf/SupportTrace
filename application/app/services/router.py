# app/services/router.py

DEPARTMENTS = {
    0: "Ассортимент",
    1: "Акции",
    2: "Доставка",
    3: "Цена",
    4: "Качество продукта",
    5: "Проблема с поддержкой",
    6: "Навигация по каталогу",
    7: "Проблемы с оплатой",
    8: "Общая поддержка"  # Добавьте этот пункт сюда!
}

def get_assigned_departments(prediction_vector) -> list:
    if hasattr(prediction_vector, "tolist"):
        vector = prediction_vector.tolist()
    else:
        vector = prediction_vector

    if isinstance(vector, list) and len(vector) > 0 and isinstance(vector[0], list):
        vector = vector[0]

    assigned = [DEPARTMENTS[i] for i, val in enumerate(vector) if val == 1 and i in DEPARTMENTS]
    
    if not assigned:
        return ["Общая поддержка"]
        
    return assigned