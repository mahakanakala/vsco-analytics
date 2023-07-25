import os
import streamlit as st
import subprocess
import boto3
import shutil
import requests
from datetime import datetime
from dotenv import load_dotenv
from transformers import ViTImageProcessor, ViTForImageClassification
from PIL import Image
import io

load_dotenv()

st.set_page_config(page_title="VSCO Analyzer",
                   page_icon=':thought_balloon:', layout='wide')

s3_client = boto3.client('s3')

def check_vsco_username_exists(vsco_username):
    url = f"https://vsco.co/{vsco_username}/gallery"
    response = requests.head(url)
    return response.status_code == 200

def is_username_processed(vsco_username):
    try:
        response = s3_client.list_objects_v2(Bucket='vsco-scrapper', Prefix='logs_username/')
        for obj in response.get('Contents', []):
            if obj['Key'].startswith('logs_username/'):
                log_key = obj['Key']
                username_in_log = log_key.split('/')[1]
                if username_in_log == vsco_username:
                    return True
        return False
    except s3_client.exceptions.NoSuchBucket:
        return False

def download_and_analyze_vsco_data(vsco_username):
    # Check if the username has already been processed
    if is_username_processed(vsco_username):
        st.info(f"VSCO username '{vsco_username}' has already been processed. Skipping download.")
        return

    # Download VSCO data using vsco-scraper
    try:
        subprocess.run(f"vsco-scraper {vsco_username} --getImages --getCollection --getProfile", shell=True, check=True)
    except subprocess.CalledProcessError:
        st.warning("Error occurred during data download. Please try again later.")
        return

    # Move the downloaded data to the temp_data directory
    local_path_to_data = f"./{vsco_username}"
    temp_data_dir = "./temp_data"
    os.makedirs(temp_data_dir, exist_ok=True)
    for root, _, files in os.walk(local_path_to_data):
        for file in files:
            relative_path = os.path.relpath(root, local_path_to_data)
            s3_key = f'{vsco_username}/{relative_path}/{file}'
            s3_client.upload_file(os.path.join(root, file), 'vsco-scrapper', s3_key)

    # Remove the temp_data directory to avoid cluttering
    shutil.rmtree(temp_data_dir)
    shutil.rmtree(local_path_to_data)

    # AI analysis on images in the journal
    predicted_classes = perform_ai_analysis(vsco_username)

    # Display the predicted classes in Streamlit
    if predicted_classes:
        st.subheader("Predicted Classes for Images in the Feed:")
        for i, predicted_class in enumerate(predicted_classes, start=1):
            st.text(f"Image {i}: {predicted_class}")
    else:
        st.warning("No images found in the journal or AI analysis results.")

    # Update the log file with the processed username
    update_log(vsco_username)

    return None 

def fetch_feed_images(vsco_username):
    # Fetch feed images from S3
    feed_images = []
    feed_prefix = f"{vsco_username}/"
    try:
        response = s3_client.list_objects_v2(Bucket='vsco-scrapper', Prefix=feed_prefix)
        for obj in response.get('Contents', []):
            image_key = obj['Key']
            # Exclude profile and collection images
            if not image_key.startswith(f"{vsco_username}/profile/") and not image_key.startswith(f"{vsco_username}/collection/"):
                response = s3_client.get_object(Bucket='vsco-scrapper', Key=image_key)
                image_data = response['Body'].read()
                feed_images.append(image_data)
    except s3_client.exceptions.NoSuchBucket:
        pass

    return feed_images

def perform_ai_analysis(vsco_username):
    feed_images = fetch_feed_images(vsco_username)

    predicted_classes = []
    processor = ViTImageProcessor.from_pretrained('google/vit-base-patch16-224')
    model = ViTForImageClassification.from_pretrained('google/vit-base-patch16-224')

    for image_data in feed_images:
        image = Image.open(io.BytesIO(image_data))
        inputs = processor(images=image, return_tensors="pt")
        outputs = model(**inputs)
        logits = outputs.logits
        # model predicts one of the 1000 ImageNet classes
        predicted_class_idx = logits.argmax(-1).item()
        predicted_class = model.config.id2label[predicted_class_idx]
        predicted_classes.append(predicted_class)
    return predicted_classes

def execute_vsco_scrapper_notebook_script(vsco_username):
    cmd = f"python script.py {vsco_username}"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout, stderr

# UPDATE AWS S3 USERNAME_LOG
def update_log(vsco_username):
    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = f"{vsco_username}_{timestamp}.txt"

    try:
        s3_client.put_object(Body=vsco_username, Bucket='vsco-scrapper', Key=f'logs_username/{log_filename}')
    except Exception as e:
        st.warning("Failed to update log. Please try again later.")
        print(e)

def main():
    vsco_username = st.text_input("Enter VSCO Username", "")
    # Button to trigger data retrieval and analysis
    if st.button("Analyze"):
        if vsco_username:
            if check_vsco_username_exists(vsco_username):
                try:
                    # Download data and perform analysis THIS WORKS
                    # download_and_analyze_vsco_data(vsco_username)
                    # Execute the Jupyter Notebook script with the username
                    stdout, stderr = execute_vsco_scrapper_notebook_script(vsco_username)
                    st.success("Data processing completed successfully.")
                except Exception as e:
                    st.error("An error occurred during data processing. Please try again later.")
                    print(e)
            else:
                st.warning("Username not found or doesn't exist. Please make sure to spell it correctly.")
        else:
            st.warning("Please enter a valid VSCO username.")

if __name__ == "__main__":
    main()