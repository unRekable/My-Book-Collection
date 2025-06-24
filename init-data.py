import os
from datetime import date
from app import app, db, Author, Book

with app.app_context():
    print("Adding initial data to the database...")

    author1 = Author(name="J.R.R. Tolkien", birth_date=date(1892, 1, 3), date_of_death=date(1973, 9, 2))
    author2 = Author(name="Jane Austen", birth_date=date(1775, 12, 16), date_of_death=date(1817, 7, 18))
    author3 = Author(name="George Orwell", birth_date=date(1903, 6, 25), date_of_death=date(1950, 1, 21))

    db.session.add_all([author1, author2, author3])
    db.session.commit()
    print("Authors added.")

    book1 = Book(
        isbn="9780618053267",
        title="The Hobbit",
        publication_year="1937",
        author=author1
    )
    book2 = Book(
        isbn="9780618260276",
        title="The Lord of the Rings",
        publication_year="1954",
        author=author1
    )
    book3 = Book(
        isbn="9780141439518",
        title="Pride and Prejudice",
        publication_year="1813",
        author=author2
    )
    book4 = Book(
        isbn="9780451524935",
        title="1984",
        publication_year="1949",
        author=author3
    )
    book5 = Book(
        isbn="9780451526342",
        title="Animal Farm",
        publication_year="1945",
        author=author3
    )

    db.session.add_all([book1, book2, book3, book4, book5])
    db.session.commit()
    print("Books added.")

    print("Initial data setup complete!")