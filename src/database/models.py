from sqlalchemy import create_engine, Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Episode(Base):
    __tablename__ = 'episodes'
    id = Column(Integer, primary_key=True)
    name = Column(String)  # Например, 'episode_28'
    focal_length = Column(Float)

class Detection(Base):
    __tablename__ = 'detections'
    id = Column(Integer, primary_key=True)
    episode_id = Column(Integer, ForeignKey('episodes.id'))
    frame = Column(Integer)
    label = Column(String)
    # 3D координаты
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    # 3D размеры
    w = Column(Float)
    h = Column(Float)
    l = Column(Float)

# Инициализация БД
def init_db(db_path="sqlite:///parking.db"):
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()