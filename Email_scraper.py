import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

# Page title
st.title("Email Scraper")

# File uploader
uploaded_file = st.file_uploader("Upload your file", type=["csv", "txt", "xlsx"])

# Initialize variables
file_valid = False
df = None

if uploaded_file is not None:
    # Determine file type and read accordingly
    file_type = uploaded_file.name.split('.')[-1]

    try:
        if file_type == "xlsx":
            df = pd.read_excel(uploaded_file)
        elif file_type == "csv":
            df = pd.read_csv(uploaded_file)
        elif file_type == "txt":
            df = pd.read_csv(uploaded_file, delimiter="\t")
        else:
            st.error("Unsupported file type.")
            df = None

        if df is not None:
            # Check if the DataFrame has the required headers
            required_headers = {"Title", "Link"}
            actual_headers = set(df.columns)

            if not required_headers.issubset(actual_headers):
                st.error(f"File must have the following headers: {', '.join(required_headers)}")
            else:
                file_valid = True
                st.write("File content:")

                # Define page size and initialize session state for pagination
                PAGE_SIZE = 10
                if 'page' not in st.session_state:
                    st.session_state.page = 0

                # Calculate total pages
                total_pages = (len(df) // PAGE_SIZE) + (1 if len(df) % PAGE_SIZE > 0 else 0)
                
                # Display the current page of data
                start_row = st.session_state.page * PAGE_SIZE
                end_row = start_row + PAGE_SIZE
                st.dataframe(df.iloc[start_row:end_row])

                # Navigation buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.session_state.page > 0:
                        if st.button("Previous", key="prev"):
                            st.session_state.page -= 1
                    
                with col2:
                    if st.session_state.page < total_pages - 1:
                        if st.button("Next", key="next"):
                            st.session_state.page += 1

    except Exception as e:
        st.error(f"An error occurred: {e}")

# Show the "Scrap Mails" button only if the file is valid
if file_valid:
    if st.button("Scrap Mails"):
        scraped_data = []
        num_links = len(df)
        progress_bar = st.progress(0)

        # Initialize progress text
        progress_text = st.empty()
        
        # Set up Firefox options for headless mode
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        
        # Initialize Selenium WebDriver with Firefox in headless mode
        driver = webdriver.Firefox(options=firefox_options)
        
        for index, row in df.iterrows():
            link = row['Link']
            title = row['Title']

            try:
                driver.get(link)
                
                # Find qualification
                qualification_elem = driver.find_element(By.XPATH, "//p[@property='qualification']")
                qualification = qualification_elem.text if qualification_elem else "No qualification found"

                # Find and click the apply button
                try:
                    apply_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "applynowbutton"))
                    )
                    apply_button.click()
                    time.sleep(2)  # Wait for 2 seconds
                except Exception as e:
                    st.warning(f"Could not click apply button for {link}: {e}")

                # Find the how to apply div and extract email
                try:
                    how_to_apply_div = driver.find_element(By.ID, "howtoapply")
                    div_text = how_to_apply_div.text
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, div_text)
                    email = emails[0] if emails else "No email found"
                except Exception as e:
                    email = f"Error finding email: {e}"

                scraped_data.append({
                    'Title': title,
                    'Link': link,
                    'Qualification': qualification,
                    'Email': email
                })
                
            except Exception as e:
                st.error(f"Error scraping {link}: {e}")

            # Update progress bar and text
            progress = (index + 1) / num_links
            progress_bar.progress(progress)
            progress_text.text(f"Progress: {index + 1}/{num_links} ({progress * 100:.1f}%)")
        
        driver.quit()  # Close the browser

        # Save the scraped data to an Excel file
        if scraped_data:
            df_scraped = pd.DataFrame(scraped_data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_scraped.to_excel(writer, index=False, sheet_name='Scraped Data')
            st.download_button(
                label="Download Scraped Data",
                data=output.getvalue(),
                file_name="scraped_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("Scraping completed and file is ready for download.")
        else:
            st.warning("No data was scraped.")