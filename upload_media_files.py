from pathlib import Path

import gridfs
from pymongo import MongoClient

DATABASE_NAME = "readersDb"
ARTICLES_DIR_PATH = Path("db-generation/articles")
MEDIA_FILES_MONGO_URI = "mongodb://localhost:27041"


def iter_files(directory: Path):
    if not directory.exists():
        print(f"Directory {directory} does not exist.")
        return []
    files = [path for path in directory.iterdir() if path.is_file()]
    if not files:
        print(f"No files found in directory {directory}.")
    return files


def upload_files(bucket: gridfs.GridFS, directory: Path):
    for file_path in iter_files(directory):
        with file_path.open("rb") as file_handle:
            if bucket.exists({"filename": file_path.name}):
                print(f"File {file_path.name} already exists in GridFS. Skipping...")
                continue
            file_id = bucket.put(file_handle, filename=file_path.name)
            print(f"Uploaded {file_path.name} with file_id {file_id}")


def main():
    client = MongoClient(MEDIA_FILES_MONGO_URI)
    db = client[DATABASE_NAME]
    bucket = gridfs.GridFS(db)

    for directory in ARTICLES_DIR_PATH.iterdir():
        if directory.is_dir():
            upload_files(bucket, directory)


if __name__ == "__main__":
    main()
