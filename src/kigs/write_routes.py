from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field, StringConstraints
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from .database import get_session
from .models import SchoolClass, Student
from .read_routes import ClassResponse, StudentResponse

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_session)]
IfMatchHeader = Annotated[str | None, Header()]
NonBlankName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class StudentCreate(BaseModel):
    first_name: NonBlankName
    last_name: NonBlankName
    email: EmailStr


class StudentUpdate(StudentCreate):
    version: int = Field(ge=1)


class ClassCreate(BaseModel):
    name: NonBlankName
    subject: NonBlankName
    student_id: int = Field(gt=0)


def _matches_if_match(if_match: str, version: int) -> bool:
    current_etag = f'"{version}"'
    return any(tag.strip() in {"*", current_etag} for tag in if_match.split(","))


@router.post(
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


@router.post(
    "/classes",
    response_model=ClassResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_class(
    class_data: ClassCreate,
    database_session: DatabaseSession,
) -> SchoolClass:
    if database_session.get(Student, class_data.student_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    school_class = SchoolClass(
        name=class_data.name,
        subject=class_data.subject,
        student_id=class_data.student_id,
    )
    database_session.add(school_class)
    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        if getattr(getattr(error.orig, "diag", None), "constraint_name", None) == "classes_student_id_fkey":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Student was deleted while creating the class",
            ) from error
        raise
    database_session.refresh(school_class)
    return school_class


@router.put("/students/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    student_data: StudentUpdate,
    database_session: DatabaseSession,
    response: Response,
    if_match: IfMatchHeader = None,
) -> Student:
    student = database_session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if if_match is not None and not _matches_if_match(if_match, student.version):
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="If-Match does not match the current student version",
        )
    if student.version != student_data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student has changed; fetch the latest version and retry",
        )

    student.first_name = student_data.first_name
    student.last_name = student_data.last_name
    student.email = str(student_data.email)
    try:
        database_session.commit()
    except StaleDataError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=(
                status.HTTP_412_PRECONDITION_FAILED
                if if_match is not None
                else status.HTTP_409_CONFLICT
            ),
            detail="Student was updated concurrently; fetch the latest version and retry",
        ) from error
    except IntegrityError as error:
        database_session.rollback()
        if getattr(getattr(error.orig, "diag", None), "constraint_name", None) == "students_email_key":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A student with this email already exists",
            ) from error
        raise
    database_session.refresh(student)
    response.headers["ETag"] = f'"{student.version}"'
    return student


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    database_session: DatabaseSession,
    if_match: IfMatchHeader = None,
) -> Response:
    student = database_session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if if_match is not None and not _matches_if_match(if_match, student.version):
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="If-Match does not match the current student version",
        )

    try:
        database_session.delete(student)
        database_session.commit()
    except StaleDataError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=(
                status.HTTP_412_PRECONDITION_FAILED
                if if_match is not None
                else status.HTTP_409_CONFLICT
            ),
            detail="Student was updated concurrently; fetch the latest version and retry",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)