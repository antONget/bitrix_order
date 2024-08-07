from sqlalchemy import BigInteger, ForeignKey, String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

from typing import List

engine = create_async_engine(url="sqlite+aiosqlite:///database/db.sqlite3", echo=False)
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(20))
    tg_id = mapped_column(BigInteger, default=0)
    username: Mapped[str] = mapped_column(String(20), default='username')
    role: Mapped[str] = mapped_column(String(200), default='user')
    balance: Mapped[float] = mapped_column(Float, default=0)


class Role(Base):
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(20))


class StatusOrder(Base):
    __tablename__ = 'status_order'

    id: Mapped[int] = mapped_column(primary_key=True)
    status_order: Mapped[str] = mapped_column(String(20))


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    id_bitrix: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10))
    data_create: Mapped[str] = mapped_column(String(40))
    data_work: Mapped[str] = mapped_column(String(40), default='None')
    data_complete: Mapped[str] = mapped_column(String(40), default='None')
    tg_create: Mapped[int] = mapped_column(Integer)
    tg_executor: Mapped[int] = mapped_column(Integer, default='0')
    client_name: Mapped[str] = mapped_column(String)
    client_second_name: Mapped[str] = mapped_column(String)
    client_last_name: Mapped[str] = mapped_column(String)
    client_phone: Mapped[str] = mapped_column(String)
    task_type_work: Mapped[str] = mapped_column(String)
    task_detail: Mapped[str] = mapped_column(String)
    task_saratov: Mapped[str] = mapped_column(String)
    task_engels: Mapped[str] = mapped_column(String)
    task_street: Mapped[str] = mapped_column(String)
    task_pay: Mapped[str] = mapped_column(String)
    task_begin: Mapped[str] = mapped_column(String)
    order_detail_text: Mapped[str] = mapped_column(String, default='None')
    order_detail_photo: Mapped[str] = mapped_column(String, default='None')
    reason_of_refusal: Mapped[str] = mapped_column(String, default='None')
    amount: Mapped[float] = mapped_column(Float, default=0)


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# import asyncio
#
# asyncio.run(async_main())
