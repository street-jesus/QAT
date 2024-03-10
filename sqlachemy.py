from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.orm import declarative_base
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine('sqlite:///:memory:')

# Define a simple model
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    name = Column(String(50))
    age = Column(Integer)

    #to prevent the code from giving out a memory address
    def __str__(self):
        return f"User(id={self.id}, name='{self.name}', age={self.age})"
# Create the table in the database
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

new_user = User(name = "Keside", age = 21)
session.add(new_user)
session.commit()

users = session.query(User).all()
for user in users:
    print(user)
