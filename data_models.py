from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Author(db.Model):
    """
    Author model representing a book author in the database.
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    # Storing dates as strings as per previous discussion for simplicity with HTML date input
    birth_date = db.Column(db.String(10), nullable=False)
    date_of_death = db.Column(db.String(10), nullable=True)

    def __str__(self):
        """
        String representation of the Author object.
        """
        return self.name

    def __repr__(self):
        """
        Official representation of the Author object for debugging.
        """
        return f'<Author {self.name!r}>' # Using f-string for repr

class Book(db.Model):
    """
    Book model representing a book in the database.
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isbn = db.Column(db.String(20), nullable=False, unique=True) # Added unique constraint
    title = db.Column(db.String(100), nullable=False)
    # Storing publication year as string (e.g., "1999")
    publication_year = db.Column(db.String(4), nullable=False) # Changed to 4 for year
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'), nullable=False)

    # Defines the relationship to the Author model
    # This allows accessing book.author and author.books
    author = db.relationship('Author', backref=db.backref('books', lazy=True))

    def __repr__(self):
        """
        Official representation of the Book object for debugging.
        """
        return f'<Book {self.title!r}>' # Using f-string for repr

    def __str__(self):
        """
        String representation of the Book object.
        """
        return self.title

