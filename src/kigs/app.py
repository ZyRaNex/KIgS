from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .models import SchoolClass, Student


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    subject: str
    student_id: int

app = FastAPI()


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello from kigs!"}


@app.get("/students", response_model=list[StudentResponse])
def read_students(database_session: Session = Depends(get_session)) -> list[Student]:
    statement = select(Student).order_by(Student.id)
    return list(database_session.scalars(statement).all())


@app.get("/students/{student_id}", response_model=StudentResponse)
def read_student(
    student_id: int,
    database_session: Session = Depends(get_session),
) -> Student:
    student = database_session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.get("/students/{student_id}/classes", response_model=list[ClassResponse])
def read_student_classes(
    student_id: int,
    database_session: Session = Depends(get_session),
) -> list[SchoolClass]:
    if database_session.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    statement = (
        select(SchoolClass)
        .where(SchoolClass.student_id == student_id)
        .order_by(SchoolClass.id)
    )
    return list(database_session.scalars(statement).all())


@app.get("/classes", response_model=list[ClassResponse])
def read_classes(database_session: Session = Depends(get_session)) -> list[SchoolClass]:
    statement = select(SchoolClass).order_by(SchoolClass.id)
    return list(database_session.scalars(statement).all())