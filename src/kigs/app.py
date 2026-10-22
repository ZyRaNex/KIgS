from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_session
from .models import SchoolClass, Student

DatabaseSession = Annotated[Session, Depends(get_session)]


NonBlankName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class StudentCreate(BaseModel):
    first_name: NonBlankName
    last_name: NonBlankName
    email: EmailStr


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


@app.post(
    "/students",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_student(
    student_data: StudentCreate,
    database_session: DatabaseSession,
) -> Student:
    student = Student(
        first_name=student_data.first_name,
        last_name=student_data.last_name,
        email=str(student_data.email),
    )
    database_session.add(student)
    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        if getattr(getattr(error.orig, "diag", None), "constraint_name", None) == "students_email_key":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A student with this email already exists",
            ) from error
        raise
    database_session.refresh(student)
    return student


@app.get("/students", response_model=list[StudentResponse])
def read_students(database_session: DatabaseSession) -> list[Student]:
    statement = select(Student).order_by(Student.id)
    return list(database_session.scalars(statement).all())


@app.get("/students/{student_id}", response_model=StudentResponse)
def read_student(
    student_id: int,
    database_session: DatabaseSession,
) -> Student:
    student = database_session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.get("/students/{student_id}/classes", response_model=list[ClassResponse])
def read_student_classes(
    student_id: int,
    database_session: DatabaseSession,
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
def read_classes(database_session: DatabaseSession) -> list[SchoolClass]:
    statement = select(SchoolClass).order_by(SchoolClass.id)
    return list(database_session.scalars(statement).all())