import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_  # Import or_ for OR conditions in queries
from datetime import date  # For date object handling

# Assume 'db', 'Author', 'Book' are defined in data_models.py
# Ensure data_models.py is correctly imported
from data_models import db, Author, Book

app = Flask(__name__)

# Configure the database with an absolute path
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'data', 'library.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Important setting for Flask-SQLAlchemy

# IMPORTANT: Set a secret key for Flask sessions (for Flash messages)
# Replace with a strong, random key in production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '34fD43!f5G//6&34!#34')

db.init_app(app)


def get_cover_image_url(isbn: str) -> str:
    """
    Fetches the URL for a book cover from the Open Library API.
    Uses the standard 'M' (Medium) size.

    Args:
        isbn (str): The ISBN of the book.

    Returns:
        str: The URL to the cover image, or None if ISBN is not provided.
    """
    if not isbn:
        return None

    # Open Library API endpoint for cover images
    # https://openlibrary.org/dev/docs/api/covers
    # Sizes: S = small, M = medium, L = large
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"


@app.route('/')
def index():
    """
    Renders the homepage displaying all books, with sorting and search functionality.
    """
    # Retrieve sorting parameter from the URL, default to 'title'
    sort_by = request.args.get('sort_by', 'title')
    # Retrieve search query from the URL, default to empty string
    search_query = request.args.get('search_query', '').strip()  # .strip() removes leading/trailing whitespace

    # Initialize SQLAlchemy query to select all Book objects
    query = db.select(Book)

    if search_query:
        # If a search query is present, filter by title OR author name (case-insensitive)
        # Join Author table to search by author's name
        query = query.join(Author).filter(
            or_(
                Book.title.ilike(f'%{search_query}%'),
                Author.name.ilike(f'%{search_query}%')
            )
        )

    # Apply sorting based on the 'sort_by' parameter
    if sort_by == 'title':
        query = query.order_by(Book.title)
    elif sort_by == 'author':
        # Ensure Author table is joined if sorting by author,
        # even if no search was performed (as it might not be joined above)
        # This check prevents redundant joins if search_query already joined it
        if not search_query or not any(
                isinstance(c, db.sql.base.Column) and c.table.name == 'author' for c in query._where_criteria):
            query = query.join(Author)
        query = query.order_by(Author.name)
    else:
        # Fallback sorting for unknown or missing sort_by parameters
        query = query.order_by(Book.title)

    # Execute the constructed query and retrieve all results
    books_db_objects = db.session.execute(query).scalars().all()

    # Prepare book data for the template (add cover URL and author name)
    books_for_template = []
    for book in books_db_objects:
        book_data = {
            'id': book.id,
            'title': book.title,
            # Safely get author name; book.author is the relationship object
            'author_name': book.author.name if book.author else "Unknown Author",
            'isbn': book.isbn,
            'publication_year': book.publication_year,
            'cover_url': get_cover_image_url(book.isbn)
        }
        books_for_template.append(book_data)

    # Render the home.html template, passing the prepared book data and parameters
    return render_template('home.html', books=books_for_template,
                           sort_by=sort_by, search_query=search_query)


@app.route('/add_author', methods=['GET', 'POST'])
def add_author():
    """
    Handles adding new authors to the database.
    GET: Displays the add author form.
    POST: Processes the form submission.
    """
    if request.method == 'POST':
        name = request.form.get('name')
        birthdate_str = request.form.get('birthdate')
        date_of_death_str = request.form.get('date_of_death')

        # Input validation for name
        if not name or not name.strip():
            flash("Author name cannot be empty.", 'error')
            return render_template('add_author.html', name=name, birthdate=birthdate_str,
                                   date_of_death=date_of_death_str)

        # Convert birthdate string to Python date object
        try:
            birthdate = date.fromisoformat(birthdate_str)
        except ValueError:
            flash("Invalid birthdate format. Please use YYYY-MM-DD.", 'error')
            return render_template('add_author.html', name=name, birthdate=birthdate_str,
                                   date_of_death=date_of_death_str)

        # Convert date of death string to Python date object if provided
        date_of_death = None
        if date_of_death_str:
            try:
                date_of_death = date.fromisoformat(date_of_death_str)
            except ValueError:
                flash("Invalid date of death format. Please use YYYY-MM-DD.", 'error')
                return render_template('add_author.html', name=name, birthdate=birthdate_str,
                                       date_of_death=date_of_death_str)

        try:
            # Create and add the new Author object to the session
            new_author = Author(name=name, birth_date=birthdate_str, date_of_death=date_of_death_str)  # Store as string
            db.session.add(new_author)
            db.session.commit()
            flash(f'Author "{name}" has been successfully added!', 'success')
            # Redirect to clear the form and display the flash message (Post/Redirect/Get pattern)
            return redirect(url_for('add_author'))
        except Exception as e:
            db.session.rollback()  # Rollback in case of error (e.g., unique constraint violation if added)
            flash(f'Error adding author: {e}', 'error')
            return render_template('add_author.html', name=name, birthdate=birthdate_str,
                                   date_of_death=date_of_death_str)
    else:
        # For GET requests, display the empty form
        return render_template('add_author.html')


@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    """
    Handles adding new books to the database.
    GET: Displays the add book form with a list of authors.
    POST: Processes the form submission.
    """
    # Retrieve all authors for the dropdown menu on both GET and POST for error re-rendering
    authors = db.session.execute(db.select(Author)).scalars().all()

    if request.method == 'POST':
        isbn = request.form.get('isbn')
        title = request.form.get('title')
        publication_year = request.form.get('publication_year')
        author_id_str = request.form.get('author_id')  # Get as string first

        # Input validation for ISBN, title, publication_year
        if not isbn or not isbn.strip():
            flash("ISBN cannot be empty.", 'error')
        elif not title or not title.strip():
            flash("Title cannot be empty.", 'error')
        elif not publication_year or not publication_year.strip() or not publication_year.isdigit() or len(
                publication_year) != 4:
            flash("Publication Year must be a 4-digit number.", 'error')

        # If any flash message was set, re-render the form with error and existing data
        if request.flashes:  # Check if flash messages were added
            return render_template('add_book.html', isbn=isbn, title=title,
                                   publication_year=publication_year,
                                   author_id=author_id_str, authors=authors)

        # Convert author_id to integer and validate
        try:
            author_id = int(author_id_str)
        except (ValueError, TypeError):
            flash("Invalid Author selected. Please choose from the list.", 'error')
            return render_template('add_book.html', isbn=isbn, title=title,
                                   publication_year=publication_year,
                                   author_id=author_id_str, authors=authors)

        author_obj = db.session.get(Author, author_id)
        if not author_obj:
            flash("Selected author does not exist in the database.", 'error')
            return render_template('add_book.html', isbn=isbn, title=title,
                                   publication_year=publication_year,
                                   author_id=author_id_str, authors=authors)

        try:
            # Create and add the new Book object to the session
            new_book = Book(
                isbn=isbn,
                title=title,
                publication_year=publication_year,
                author=author_obj  # Pass the Author object directly
            )
            db.session.add(new_book)
            db.session.commit()

            flash(f'Book "{title}" by {author_obj.name} has been successfully added!', 'success')
            # Redirect after adding to clear the form and display flash message
            return redirect(url_for('add_book'))
        except Exception as e:
            db.session.rollback()  # Rollback in case of error (e.g., unique ISBN constraint violation)
            flash(f'Error adding book: {e}', 'error')
            return render_template('add_book.html', isbn=isbn, title=title,
                                   publication_year=publication_year,
                                   author_id=author_id_str, authors=authors)

    else:
        # For GET requests: Retrieve all authors for the dropdown menu
        return render_template('add_book.html', authors=authors)


@app.route('/book/<int:book_id>/delete', methods=['POST'])
def delete_book(book_id):
    """
    Deletes a specific book from the database.
    Redirects to the homepage with a success/error message.
    """
    # Find the book by its ID
    book_to_delete = db.session.get(Book, book_id)

    if book_to_delete:
        try:
            book_title = book_to_delete.title  # Store title for flash message before deletion
            db.session.delete(book_to_delete)
            db.session.commit()
            flash(f'Book "{book_title}" has been successfully deleted.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting book "{book_title}": {e}', 'error')
    else:
        flash('Book not found.', 'error')

    return redirect(url_for('index'))  # Redirect to homepage after deletion


# Custom error handler for 404 Not Found
@app.errorhandler(404)
def page_not_found(e):
    """
    Handles 404 Not Found errors.
    """
    return render_template('404.html'), 404  # Assuming you have a 404.html template


# Example for database initialization (run this once to create tables)
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=)
