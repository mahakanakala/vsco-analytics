import os
import streamlit as st
import subprocess
import boto3
import shutil
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="VSCO Analyzer",
                   page_icon=':thought_balloon:', layout='wide')

# Initialize AWS S3 client
s3_client = boto3.client('s3')

with st.container():
    st.subheader("Analyze your VSCO using this!")
    st.title("VSCO Analytics App")
    st.markdown(
        "This app analyzes your VSCO data and generates insights about your VSCO profile, posts, and journals.")

def main():
    vsco_username = st.text_input("Enter VSCO Username", "")

    # Check if the temp_data directory existsm, if not, create the directory
    if not os.path.exists('./temp_data'):
        #
        os.makedirs('./temp_data')

    # Check if the app has write permissions for the temp_data directory
    if not os.access('./temp_data', os.W_OK):
        st.warning("Permission denied: Cannot write to temp_data directory.")

    # Button to trigger data retrieval and upload to S3
    if st.button("Analyze"):
        if vsco_username:
            # Call vsco-scraper CLI commands using subprocess
            subprocess.run(
                f"vsco-scraper {vsco_username} --getImages --getCollection --getProfile", shell=True, check=True)

            # Move the downloaded data to the temp_data directory
            local_path_to_data = f"./{vsco_username}"
            temp_data_dir = "./temp_data"
            os.makedirs(temp_data_dir, exist_ok=True)
            for root, _, files in os.walk(local_path_to_data):
                for file in files:
                    shutil.move(os.path.join(root, file), temp_data_dir)

            # Upload the data from the temp_data directory to the S3 bucket
            for file in os.listdir(temp_data_dir):
                s3_key = f'{vsco_username}/{file}'
                s3_client.upload_file(os.path.join(
                    temp_data_dir, file), 'vsco-scrapper', s3_key)

            # Remove the temp_data directory to avoid cluttering
            shutil.rmtree(temp_data_dir)
            shutil.rmtree(local_path_to_data)

            # Process the downloaded data and perform visualizations
            # Your code for data processing and visualization here

            # Display visualizations using Streamlit's plotting functions
            # st.plotly_chart, st.image, etc.
        else:
            st.warning("Please enter a valid VSCO username.")

if __name__ == "__main__":
    main()
