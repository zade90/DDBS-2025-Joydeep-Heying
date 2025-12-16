# Mocking Distributed Databases

This project demonstrates the setup of a sharded MongoDB cluster using Docker. 



## Steps to Run the Project

### Clone the Repository

Clone this repository to your local machine and navigate into the project directory:

```bash
git clone git@github.com:nonlinearjunkie/Mocking-Distributed-Databases.git
cd Mocking-Distributed-Databases
```

### Change Permissions of Bash Scripts
Make the setup and data-loading scripts executable:

```bash
chmod +x setup_mongo_cluster.sh
chmod +x load_data_mongodb.sh
```

### Set Up the MongoDB Cluster
Run the setup script to create the sharded MongoDB cluster:

```bash
./setup_mongo_cluster.sh
```

### Prepare Data for MongoDB
Before running the following scripts, ensure you have downloaded the data generation script and placed the generated files inside the `db-generation` directory, which is located in the root of the project.

### Set Up the MongoDB Cluster
Once the cluster is running, use the following script to load the data into MongoDB:

```bash
./load_data_mongodb.sh
```

### Bulk Load files
Use the following script to bulk load the article files into MongoDB Grid FS:

```bash
python upload_media.py
```

### Run background tasks to update sci_articles collection and popular ranks on update

```bash
python refresh_article_update.py
python refresh_read_update.py
```

### Start the fastpi server:

```bash
uvicorn main:app --host 0.0.0.0 --port 20000
```


## Notes

- All bash scripts are designed for Linux. If you're using Windows, run them using **WSL (Windows Subsystem for Linux)**.

