import os
import click
import psycopg2
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

def setup_database():
    try:
        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(database=DB_NAME, user=USER, password=PASSWORD, host=HOST, port=PORT)
        cur = conn.cursor()

        # create table one by one
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
        reader = Reader(['en', 'pl'])
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
@click.argument('directory')
def load_and_index_image_dir(directory):
    # List of common image extensions
    valid_extensions = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')

    # get all files
    files = []
    for foldername, _ , filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(valid_extensions):
                files.append(os.path.join(foldername, filename))

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
