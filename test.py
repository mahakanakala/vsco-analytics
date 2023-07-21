import os
import boto3
from dotenv import load_dotenv

s3_client = boto3.client('s3')

# response = s3_client.upload_file("./temp_data/1667536427.jpg","vsco-scrapper","image.jpg")

def upload_images_to_bucket(username):
    temp_data_dir = f"./temp_data/{username}"

    for root, _, files in os.walk(temp_data_dir):
        for filename in files:
            local_path = os.path.join(root, filename)
            s3_key = f"{username}/{filename}"
            s3_client.upload_file(local_path, "vsco-scrapper", s3_key)

def main():
    vsco_username = 'maha-kanakala'

    # Check if the temp_data directory exists
    if not os.path.exists('./temp_data'):
        print("temp_data directory does not exist. Please create the required folders.")
        return
    # Check if the app has write permissions for the temp_data directory
    if not os.access('./temp_data', os.W_OK):
        print("Permission denied: Cannot write to temp_data directory.")
        return

    upload_images_to_bucket(vsco_username)

if __name__ == "__main__":
    main()