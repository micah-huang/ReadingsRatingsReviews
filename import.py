import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker



engine = create_engine("postgres://yfvsepemigiqjn:5aa8dcb42e78b05559d996dc921d6607042bff43f8f65b3ba680127b8476551a@ec2-34-234-228-127.compute-1.amazonaws.com:5432/d15o8af8uk4rnd")
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, title, author, year in reader:
    	if year == "year":
    		continue 
    	else:
        	db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                    {"isbn": isbn, "title": title, "author": author, "year": year})
    db.commit()

if __name__ == "__main__":
    main()
