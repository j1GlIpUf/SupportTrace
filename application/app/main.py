# app/main.py
from fastapi import FastAPI, HTTPException, Depends
from app.schemas.ticket import *
from app.services.classifier import classifier_service
from app.services.router import get_assigned_departments
from app.models.database import *
from sqlalchemy.orm import Session
from app.models.database import *  # Импортируйте Base из файла с моделями
from pydantic import BaseModel
from sqlalchemy import func
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth import get_password_hash, verify_password, create_access_token
from app.schemas.user import *
from app.services.auth import *
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# ЭТА СТРОКА СОЗДАЕТ ТАБЛИЦЫ
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Support Routing System")


current_dir = os.path.dirname(os.path.realpath(__file__))
static_path = os.path.join(current_dir, "static")
# Подключаем папку со статикой
app.mount("/static", StaticFiles(directory=static_path), name="static")


# Маршрут для главной страницы
@app.get("/")
async def read_index():
    return FileResponse(f"{static_path}/index.html")


@app.post("/tickets/create")
async def create_ticket(
    message: UserMessage,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Получаем предсказание от классификатора (список названий отделов)
    prediction = classifier_service.get_category(message.text)
    target_departments = get_assigned_departments(prediction)

    # 2. Создаем основной тикет
    new_ticket = Ticket(
        user_id=current_user.id,
        text=message.text,
        predicted_classes=", ".join(target_departments),
        status="distributed",
    )
    db.add(new_ticket)
    db.commit()  # Сохраняем тикет, чтобы получить его ID
    db.refresh(new_ticket)

    # 3. Создаем назначения для каждого отдела
    for dept_name in target_departments:
        assignment = TicketAssignment(
            ticket_id=new_ticket.id,
            department_name=dept_name,  # Используем строковое имя
        )
        db.add(assignment)  # Добавляем каждое назначение в сессию внутри цикла

    db.commit()

    return {
        "ticket_id": new_ticket.id,
        "author": current_user.username,
        "assigned_to": target_departments,
        "status": "distributed",
    }


@app.get("/tickets/my")
async def get_my_tickets(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Фильтруем тикеты, чтобы пользователь видел только свои
    tickets = db.query(Ticket).filter(Ticket.user_id == current_user.id).all()
    return tickets


@app.get("/tickets/department/{dept_name}")
def get_department_tickets(
    dept_name: str, db: Session = Depends(get_db), _=Depends(check_support_role)
):
    assignments = (
        db.query(TicketAssignment)
        .filter(
            TicketAssignment.department_name == dept_name,
            TicketAssignment.is_resolved == False,
        )
        .all()
    )

    # Собираем данные: берем текст из связанной таблицы Ticket
    results = []
    for am in assignments:
        results.append(
            {
                "assignment_id": am.id,
                "ticket_id": am.ticket_id,
                "text": am.ticket.text,
                "status": am.ticket.status,
            }
        )

    return {"department": dept_name, "active_tickets": results}


@app.get("/tickets/my-assignments")
async def get_my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_support_role),
):
    dept_name = current_user.department

    if not dept_name:
        return []

    tickets = (
        db.query(Ticket)
        .join(TicketAssignment, TicketAssignment.ticket_id == Ticket.id)
        .filter(
            TicketAssignment.department_name == dept_name,
            TicketAssignment.is_resolved == False,
        )
        .all()
    )
    return tickets


@app.post("/tickets/{ticket_id}/messages")
async def send_message(
    ticket_id: int,
    message_in: UserMessage,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    new_message = Message(
        ticket_id=ticket_id,
        user_id=current_user.id,  
        sender=current_user.role,
        text=message_in.text,
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return {"status": "success"}


@app.get("/tickets/all")
async def get_all_tickets(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if current_user.role == "admin":
        # Админ видит все тикеты. 
        # Добавляем фиктивный assignment_id = None, чтобы фронт не путался
        tickets = db.query(Ticket).all()
        result = []
        for t in tickets:
            d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
            d["active_assignment_id"] = None # У админа нет конкретного назначения
            result.append(d)
        return result

    if current_user.role == "support":
        # Саппорт видит тикеты, назначенные в его департамент
        # Делаем JOIN, чтобы вытащить ID из таблицы назначений
        query_results = (
            db.query(Ticket, TicketAssignment.id.label("as_id"))
            .join(TicketAssignment, Ticket.id == TicketAssignment.ticket_id)
            .filter(
                TicketAssignment.department_name == current_user.department,
                TicketAssignment.is_resolved == False
            )
            .all()
        )

        result = []
        for ticket, as_id in query_results:
            d = {c.name: getattr(ticket, c.name) for c in ticket.__table__.columns}
            d["active_assignment_id"] = as_id  # Тот самый ID, который нужен для Resolve!
            result.append(d)
        return result

    raise HTTPException(status_code=403, detail="Нет доступа")

# Получить все сообщения тикета
@app.get("/tickets/{ticket_id}/messages")
def get_messages(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  
):
    # 1. Ищем тикет
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # 2. ПРОВЕРКА ДОСТУПА:
    # Если это клиент, и ID автора тикета не совпадает с его ID — запрещаем
    if current_user.role == "user" and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Доступ запрещен: вы можете просматривать только свои тикеты",
        )

    # 3. Если проверка прошла (или это саппорт/админ) — отдаем сообщения
    messages = (
        db.query(Message)
        .filter(Message.ticket_id == ticket_id)
        .order_by(Message.timestamp)
        .all()
    )
    return messages


@app.get("/tickets/{ticket_id}/assignments")
async def get_ticket_assignments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # Саппорт видит только тикеты своего отдела
    if current_user.role == "support":
        dept_name = current_user.department

        assignment = (
            db.query(TicketAssignment)
            .filter(
                TicketAssignment.ticket_id == ticket_id,
                TicketAssignment.department_name == dept_name,
            )
            .first()
        )
        if not assignment:
            raise HTTPException(status_code=403, detail="Нет доступа к этому тикету")

    assignments = (
        db.query(TicketAssignment).filter(TicketAssignment.ticket_id == ticket_id).all()
    )

    return [
        {
            "department_name": a.department_name,
            "is_resolved": a.is_resolved,
            "assigned_at": a.assigned_at,
        }
        for a in assignments
    ]


@app.post("/tickets/assignments/{assignment_id}/reassign_multiple")
def reassign_ticket_multiple(
    assignment_id: int,
    request: ReassignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_support_role),
):
    # 1. Сначала пробуем найти назначение напрямую по ID (как as_id=14)
    old_assignment = db.query(TicketAssignment).filter(TicketAssignment.id == assignment_id).first()
    
    # 2. Если не нашли, значит передали ID тикета (как id=9). Ищем активное назначение для него.
    if not old_assignment:
        old_assignment = db.query(TicketAssignment).filter(
            TicketAssignment.ticket_id == assignment_id,
            TicketAssignment.is_resolved == False
        ).first()

    if not old_assignment:
        raise HTTPException(status_code=404, detail="Активное назначение не найдено. Возможно, оно уже закрыто или переведено.")

    ticket_id = old_assignment.ticket_id
    
    # --- НОВАЯ ЛОГИКА ДЛЯ ТОЧНОСТИ ИИ ---
    # Получаем сам тикет и помечаем, что категория была исправлена вручную
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket:
        # Записываем новые отделы как "правильную" категорию. 
        # Как только manual_category перестает быть None, точность в статистике падает.
        ticket.manual_category = ", ".join(request.new_departments)
    # ------------------------------------

    # 2. Создаем новые назначения
    for dept_name in request.new_departments:
        new_assignment = TicketAssignment(
            ticket_id=ticket_id, department_name=dept_name, is_resolved=False
        )
        db.add(new_assignment)

    # 3. Удаляем старое назначение
    db.delete(old_assignment)

    # 4. Логируем в сообщениях
    depts_str = ", ".join(request.new_departments)
    system_msg = Message(
        ticket_id=ticket_id,
        sender="system",
        text=f"Сотрудник {current_user.username} перенаправил задачу в отделы: {depts_str}. ИИ классификация признана неверной.",
    )
    db.add(system_msg)

    db.commit()

    return {
        "status": "success",
        "added_departments": request.new_departments,
        "message": f"Тикет перераспределен. Точность модели обновлена.",
    }


@app.get("/admin/dashboard/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    # 1. Считаем только завершенные тикеты
    closed_tickets = db.query(Ticket).filter(Ticket.status == 'closed')
    total_closed = closed_tickets.count()
    
    if total_closed == 0:
        return {"total_tickets": 0, "ai_accuracy_estimate": 100.0}

    # 2. Считаем тикеты, которые были закрыты БЕЗ вмешательства (manual_category ис null)
    correct_ai_tickets = closed_tickets.filter(Ticket.manual_category == None).count()
    
    # 3. Вычисляем процент по вашей формуле
    accuracy = (correct_ai_tickets / total_closed) * 100

    return {
        "total_tickets": db.query(Ticket).count(), # Всего в системе
        "closed_tickets": total_closed,            # Всего закрыто
        "ai_accuracy_estimate": round(accuracy, 2)
    }



@app.get("/admin/dashboard/department_load")
def get_dept_load(
    db: Session = Depends(get_db), 
    current_user: User = Depends(check_admin_role)
):
    # Данные для круговой диаграммы (только открытые)
    # Исправленный запрос для круговой диаграммы
    active_counts = (
    db.query(TicketAssignment.department_name, func.count(TicketAssignment.id))
    .join(Ticket, Ticket.id == TicketAssignment.ticket_id)
    .filter(TicketAssignment.is_resolved == False)
    .filter(Ticket.status != 'closed') # Если тикет закрыт, не считаем его активным!
    .group_by(TicketAssignment.department_name)
    .all()
)
    
    # Данные для столбчатой диаграммы (все заявки в базе)
    all_counts = (
        db.query(TicketAssignment.department_name, func.count(TicketAssignment.id))
        .group_by(TicketAssignment.department_name)
        .all()
    )
    
    return {
        "active": {dept: count for dept, count in active_counts},
        "all_time": {dept: count for dept, count in all_counts}
    }


@app.post("/auth/register")
async def register_client(user_data: UserCreate, db: Session = Depends(get_db)):
    # Проверка на дубликат
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Логин уже занят")

    new_user = User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),  # Хешируем!
        role="user",
        department="Вне отделов",  
    )
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": "Клиент зарегистрирован"}


@app.post("/admin/create-support", dependencies=[Depends(check_admin_role)])
async def create_support_user(
    username: str, password: str, dept_name: str, db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    new_support = User(
        username=username,
        hashed_password=get_password_hash(password),
        role="support",
        department=dept_name,
    )
    db.add(new_support)
    db.commit()
    return {"status": "success", "detail": f"Сотрудник отдела {dept_name} создан"}


@app.post("/auth/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()

    # Твоя функция verify_password теперь работает на страже
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")

    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "department": user.department,  # Передаем отдел фронтенду
    }


@app.post("/tickets/assignments/{assignment_id}/resolve")
def resolve_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_support_role),
):
    assignment = (
        db.query(TicketAssignment).filter(TicketAssignment.id == assignment_id).first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Назначение не найдено")

    # 1. Помечаем как выполненное
    assignment.is_resolved = True
    
    # СИНХРОНИЗИРУЕМ состояние с базой прямо сейчас, чтобы count() отработал верно
    db.flush() 

    ticket_id = assignment.ticket_id

    # 2. Считаем ОСТАЛЬНЫЕ открытые назначения
    remaining_open_assignments = (
        db.query(TicketAssignment)
        .filter(
            TicketAssignment.ticket_id == ticket_id,
            TicketAssignment.is_resolved == False,
        )
        .count()
    )

    status_msg = f"Отдел {assignment.department_name} завершил работу."

    # 3. Если это было последнее открытое назначение
    if remaining_open_assignments == 0:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket:
            ticket.status = "closed" # Теперь статус точно обновится
            status_msg += " Все отделы закрыли задачу. Тикет официально закрыт."

            system_msg = Message(
                ticket_id=ticket_id,
                sender="system",
                text="Заявка полностью исполнена и закрыта всеми службами.",
            )
            db.add(system_msg)

    db.commit() # Фиксируем всё разом

    return {
        "status": "success",
        "resolved_department": assignment.department_name,
        "remaining_assignments": remaining_open_assignments,
        "message": status_msg,
    }

@app.get("/tickets/{ticket_id}/current-departments")
async def get_current_departments(
    ticket_id: int, 
    db: Session = Depends(get_db), 
    _=Depends(check_support_role)
):
    assignments = (
        db.query(TicketAssignment)
        .filter(TicketAssignment.ticket_id == ticket_id, TicketAssignment.is_resolved == False)
        .all()
    )
    return [a.department_name for a in assignments]

@app.post("/tickets/{ticket_id}/admin-close")
def admin_resolve_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_role), # Убедитесь, что эта проверка только для админов
):
    # 1. Находим тикет
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # 2. Закрываем все открытые назначения для этого тикета
    open_assignments = db.query(TicketAssignment).filter(
        TicketAssignment.ticket_id == ticket_id,
        TicketAssignment.is_resolved == False
    ).all()

    for assignment in open_assignments:
        assignment.is_resolved = True

    # 3. Обновляем статус самого тикета
    ticket.status = "closed"

    # 4. Добавляем системное сообщение
    system_msg = Message(
        ticket_id=ticket_id,
        sender="system",
        text=f"Администратор {current_user.username} принудительно закрыл заявку и все связанные задачи."
    )
    db.add(system_msg)
    
    db.commit()

    return {"status": "success", "message": "Тикет и все назначения закрыты администратором"}