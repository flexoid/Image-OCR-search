import os
import click
import psycopg2
import dateparser
import time
from easyocr import Reader
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

# set up the database connection parameters
DB_NAME = os.getenv("DB_NAME")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
LANGUAGES = os.getenv("LANGUAGES").split(',')

def setup_database():
    try:
        # create database DB_NAME if it does not exist
        conn = psycopg2.connect(database='postgres', user=USER, password=PASSWORD, host=HOST, port=PORT)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cur.fetchone()
        if not exists:
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database {DB_NAME} created.")
        cur.close()
        conn.close()

        # connect to the PostgreSQL server
        conn = psycopg2.connect(database=DB_NAME, user=USER, password=PASSWORD, host=HOST, port=PORT)
        cur = conn.cursor()

        # create table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS images(
                path TEXT NOT NULL PRIMARY KEY,
                content TEXT
            )
        """)

        # close the communication with the PostgreSQL
        cur.close()
        conn.commit()
        print('Database setup complete.')
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        if conn is not None:
            conn.close()

def perform_ocr(file):
    try:
        reader = Reader(LANGUAGES)
        result = reader.readtext(file)
        text = ' '.join([item[1] for item in result])
        return text
    except Exception as e:
        print('Error in performing OCR', str(e))
        return None

def file_exists_in_db(file):
    conn = psycopg2.connect(database=DB_NAME, user=USER, password=PASSWORD, host=HOST, port=PORT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM images WHERE path = %s", (file,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None

def save_to_db(file, text):
    conn = psycopg2.connect(database=DB_NAME, user=USER, password=PASSWORD, host=HOST, port=PORT)
    cur = conn.cursor()
    cur.execute("INSERT INTO images(path, content) VALUES(%s, %s)", (file, text))
    conn.commit()

@click.group()
def cli():
    pass

@click.command(name='load_and_index')
@click.option('--since', default=None, help='Only process files created after this date. Accepts human readable dates like "1y" for one year, as well as exact dates.')
@click.argument('directory')
def load_and_index_image_dir(directory, since):
    # List of common image extensions
    valid_extensions = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')

    # if since arg added, parse the date into timestamp
    since_time = None
    if since:
        try:
            since_time = time.mktime(dateparser.parse(since).timetuple())
        except Exception as e:
            click.echo(f'Failed to parse date: {str(e)}')
            return

    # get all files
    files = []
    for foldername, _ , filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(valid_extensions):
                file_path = os.path.join(foldername, filename)
                # get file creation time
                file_time = os.path.getmtime(file_path)
                # if a since date is specified, only append files that were created after that date
                if since_time is not None and file_time < since_time:
                    continue
                files.append(file_path)

    # initialise progress
    with tqdm(total=len(files), dynamic_ncols=True) as progress:
        # iterate over files
        for file in files:
            progress.set_description("Processing %s" % file)
            # If a file has been scanned already, skip it
            if not file_exists_in_db(file):
                # Perform OCR on file
                text = perform_ocr(file)
                if text is not None:
                    save_to_db(file, text)
                else:
                    click.echo("Failed to process image: "+ file)
            progress.update(1)

@click.command(name='search')
@click.argument('query')
def search_text_in_images(query):

    try:
        # establish a database session
        conn = psycopg2.connect(database=DB_NAME, user=USER, password=PASSWORD, host=HOST, port=PORT)
        cur = conn.cursor()

        # prepare a select statement (using ILIKE for case-insensitive and full-text search)
        stmt = "SELECT path FROM images WHERE content ILIKE %s"
        cur.execute(stmt, ('%' + query + '%', ))

        rows = cur.fetchall()

        click.echo(f"Found {len(rows)} matches:")
        for row in rows:
            click.echo(row[0])

        # terminate the database session
        cur.close()
        conn.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

cli.add_command(load_and_index_image_dir)
cli.add_command(search_text_in_images)

if __name__ == '__main__':
    setup_database()
    cli()
