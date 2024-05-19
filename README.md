# Image Search CLI application with OCR

This CLI application provides an image-search functionality using Optical Character Recognition (OCR). It's written in Python 3, uses the `EasyOCR` library for image scanning, and a PostgreSQL database for storing scan results. You can index an image directory recursively and perform full-text search over the available scan results.

Personally, I find it very useful for searching all my screenshots stored in the Desktop directory.

## Installation

1. Clone the repository.

2. Change into the directory.

3. Install virtualenv:  
   `pip3 install virtualenv`
4. Create a virtual environment:  
   `virtualenv venv`

5. Activate the virtual environment:  
   On Windows, use: `venv\Scripts\Activate`  
   On macOS and Linux, use: `source venv/bin/activate`

6. Install the required dependencies:  
   `pip3 install -r requirements.txt`

7. Create a `.env` file using the provided example and update the parameters, such as the database connection details and OCR languages:

   ```
   cp .env.example .env
   ```

## Basic Usage

- To index or scan a directory recursively, use:  
   `python3 main.py load_and_index directory_path --since "interval"`  
   The `--since` parameter is optional. It selects files modified within a certain interval in a human-readable format, like "2 months ago", "3 weeks", "1 year", etc.

- To perform a full-text search over the available scan results, use:  
   `python3 main.py search your_query`  
   It outputs the list of files that contain the requested text.

## License

This project is licensed under the MIT License.
