from sqlalchemy import create_engine,Column, Integer, String, Text,UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from django.conf import settings
BASE = declarative_base()
class Command_phrase(BASE):
    __tablename__ = 'command_phrase'
    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False)
    phrase = Column(String(200), nullable=False)
    table_args = (UniqueConstraint('category', 'phrase', name='unique_category_phrase'),)
db_path = settings.DATABASES['default']['NAME']
_engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker(bind = _engine)
CATEGORIES = ("open","close","add_command","delete_command","confirm","deny","cancel","keep","add_letter","remove_letter",)
def init_db():
    BASE.metadata.create_all(_engine)
def load_phrases():
    init_db()
    commands = {
        category: [] for category in CATEGORIES
    }
    
    session = Session()
    try:
        for row in session.query(Command_phrase).all():
            commands.setdefault(row.category,[]).append(row.phrase)
    finally :
        session.close()
        return commands
def add_phrase(category : str,phrase : str):
    init_db()
    phrase = phrase.strip()
    if not phrase :
        return False
    session = Session()
    try:
        exists = (session.query(Command_phrase).filter_by(category = category, phrase = phrase,).first() )
        if exists:
            return False
        session.add(Command_phrase(category = category, phrase = phrase))
        session.commit()
        return True
    finally:
        session.close()