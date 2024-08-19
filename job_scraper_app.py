import streamlit as st
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
from tqdm import tqdm
import io


def run_scraper(url):
    options = Options()
    options.headless = False  # Run in headless mode for web app
    driver = webdriver.Firefox(options=options)
    try:
        driver.get(url)
        progress_bar = st.progress(0)
        status_text = st.empty()

        
        click_count = 0
        while True:
            try:
                morepage_div = driver.find_element(By.ID, "morepage")
                button = morepage_div.find_element(By.TAG_NAME, "button")
                button.click()
                click_count += 1
                status_text.text(f"Loaded {click_count} more pages...")
                progress_bar.progress(click_count / (click_count + 8))  # Simple progress estimation
                time.sleep(3)
            except NoSuchElementException:
                break

        status_text.text("Extracting job information...")
        data = []
        articles = driver.find_elements(By.TAG_NAME, "article")
        
        for article in articles:
            spans = article.find_elements(By.CLASS_NAME, "noctitle")
            for span in spans:
                title = span.text
                links = article.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute("href")
                    if href and "https://www.jobbank.gc.ca/login" not in href:
                        data.append({"Title": title, "Link": href})

        df = pd.DataFrame(data)
        return df

    finally:
        driver.quit()

st.title('Job Scraper 🇨🇦 👨🏻‍💻')

url = st.text_input('Enter the Job Bank search URL:', '')

if st.button('Start Scraping'):
    with st.spinner('Scraping in progress...'):
        df = run_scraper(url)
        st.write(f"Total jobs scraped: {len(df)}")
        st.dataframe(df)
        
        # Create a download button for the Excel file
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="Download Excel file",
            data=buffer,
            file_name="job_Links.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
