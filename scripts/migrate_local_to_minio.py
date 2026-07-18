import os
import sys
import glob

# Add backend root to path
sys.path.append("/home/mashupsoat/Project/resurva/resurva_backend")

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv("/home/mashupsoat/Project/resurva/resurva_backend/.env")

def get_s3_client():
    s3_access_key = os.getenv("S3_ACCESS_KEY_ID")
    s3_secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
    s3_endpoint = os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
    s3_region = os.getenv("S3_REGION_NAME", "us-east-1")
    
    return boto3.client(
        "s3",
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_key,
        endpoint_url=s3_endpoint,
        region_name=s3_region
    )

def migrate():
    bucket_name = os.getenv("S3_BUCKET_NAME", "resurva-bucket")
    uploads_dir = "/home/mashupsoat/Project/resurva/resurva_backend/uploads"
    
    print(f"Bucket target: {bucket_name}")
    print(f"Uploads local directory: {uploads_dir}")
    
    s3 = get_s3_client()
    
    # 1. Upload files
    folders = ["products", "stores"]
    for folder in folders:
        local_folder = os.path.join(uploads_dir, folder)
        if not os.path.exists(local_folder):
            print(f"Local folder {local_folder} does not exist, skipping.")
            continue
            
        print(f"\nProcessing local folder: {folder}")
        files = glob.glob(os.path.join(local_folder, "*"))
        for file_path in files:
            if os.path.isdir(file_path):
                continue
            filename = os.path.basename(file_path)
            if filename == ".gitignore":
                continue
                
            key = f"{folder}/{filename}"
            print(f"Uploading {filename} to {bucket_name}/{key}...")
            try:
                # Check if object already exists to avoid re-uploading
                try:
                    s3.head_object(Bucket=bucket_name, Key=key)
                    print(f"  Object {key} already exists in bucket, skipping upload.")
                except ClientError:
                    # Upload it
                    with open(file_path, "rb") as data:
                        s3.put_object(
                            Bucket=bucket_name,
                            Key=key,
                            Body=data,
                            ContentType="image/png" if filename.endswith(".png") else "application/octet-stream"
                        )
                    print(f"  Uploaded {key} successfully.")
            except Exception as e:
                print(f"  Failed to upload {key}: {e}")
                
    # 2. Update Database Records
    print("\nUpdating PostgreSQL database records...")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set in .env. Cannot update database.")
        return
        
    # Convert postgresql+asyncpg:// to postgresql:// for synchronous connection
    sync_db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_db_url)
    
    with engine.begin() as conn:
        # Update products
        res_prod1 = conn.execute(text("UPDATE products SET image_url = REPLACE(image_url, '/uploads/', '') WHERE image_url LIKE '/uploads/%'"))
        res_prod2 = conn.execute(text("UPDATE products SET image_url = REPLACE(image_url, 'uploads/', '') WHERE image_url LIKE 'uploads/%'"))
        print(f"Updated {res_prod1.rowcount + res_prod2.rowcount} product records.")
        
        # Update stores
        res_store1 = conn.execute(text("UPDATE stores SET image_url = REPLACE(image_url, '/uploads/', '') WHERE image_url LIKE '/uploads/%'"))
        res_store2 = conn.execute(text("UPDATE stores SET image_url = REPLACE(image_url, 'uploads/', '') WHERE image_url LIKE 'uploads/%'"))
        print(f"Updated {res_store1.rowcount + res_store2.rowcount} store records.")
        
    print("\nMigration Completed Successfully!")

if __name__ == "__main__":
    migrate()
