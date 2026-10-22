from typing import ClassVar

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "school"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    classes: Mapped[list[SchoolClass]] = relationship(back_populates="student")

    __mapper_args__: ClassVar[dict[str, object]] = {"version_id_col": version}


class SchoolClass(Base):
    __tablename__ = "classes"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "school"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("school.students.id", ondelete="CASCADE"),
        nullable=False,
    )
    student: Mapped[Student] = relationship(back_populates="classes")