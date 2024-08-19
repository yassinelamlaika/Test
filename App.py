import streamlit as st
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from tqdm import tqdm
import io
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Page 1
def page_1():
    # Job Scraper Code for Page 1
    def run_scraper(url):
        options = Options()
        options.headless = True  # Set headless mode to True
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
                    progress_bar.progress(click_count / (click_count + 8))
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
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button(
                label="Download Excel file",
                data=buffer,
                file_name="job_Links.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# Page 2
# Page title
# Page title
def page_2():
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
                output = io.BytesIO()
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
                    
    
    # Page 3

def send_email(smtp_server, smtp_port, sender_email, sender_password, recipient_email, subject, message, attachment=None):
    try:
        # Set up the email message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Attach the message body
        msg.attach(MIMEText(message, 'plain'))

        # Attach the file if provided
        if attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {attachment.name}")
            msg.attach(part)

        # Connect to the SMTP server and send the email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        server.login(sender_email, sender_password)  # Login to the email server
        server.sendmail(sender_email, recipient_email, msg.as_string())  # Send the email
        server.quit()  # Disconnect from the server

        return True
    except Exception as e:
        st.error(f"Error sending email to {recipient_email}: {str(e)}")
        return False

def page_3():
    st.title("Email Configuration")

    # SMTP Settings
    smtp_server = st.text_input("SMTP Server", "smtp.gmail.com")
    smtp_port = st.number_input("SMTP Port", value=587)
    sender_email = st.text_input("Sender Email", "fabricamaroc@gmail.com")
    sender_password = st.text_input("Sender Password", "itsy bqfi xxmw ztud", type="password")

    # Language-specific inputs
    en_subject = st.text_input("🇬🇧 EN Subject")
    fr_subject = st.text_input("🇫🇷 FR Subject")
    en_message = st.text_area("🇬🇧 EN Message")
    fr_message = st.text_area("🇫🇷 FR Message")

    # File uploads
    en_attach = st.file_uploader("🇬🇧 EN Attachment", accept_multiple_files=False)
    fr_attach = st.file_uploader("🇫🇷 FR Attachment", accept_multiple_files=False)

    # Contacts file upload
    contacts_file = st.file_uploader("Upload Contacts (Excel file)", type=["xlsx", "xls"])

    # Send Button
    if st.button("Send Emails"):
        if contacts_file is None:
            st.error("Please upload a contacts file.")
            return

        try:
            # Load contacts file
            df = pd.read_excel(contacts_file)

            if "Qualification" not in df.columns or "Email" not in df.columns:
                st.error("The contacts file must have 'Qualification' and 'Email' columns.")
                return

            # Filter rows to send a max of 100 emails
            df_to_send = df.head(100)  # Select first 2 rows

            if df_to_send.empty:
                st.info("No more emails to send!")
                return

            # Initialize progress bar
            total_emails = len(df_to_send)
            progress = st.progress(0)
            status_text = st.empty()  # Placeholder for status messages

            # Send emails for the selected contacts
            for index, row in df_to_send.iterrows():
                qualification = row["Qualification"]
                recipient_email = row["Email"]

                if qualification.lower() == "english":
                    subject = en_subject
                    message = en_message
                    attachment = en_attach
                elif qualification.lower() == "french":
                    subject = fr_subject
                    message = fr_message
                    attachment = fr_attach
                elif qualification.lower() == "English or French":
                    subject = en_subject
                    message = en_message
                    attachment = en_attach
                else:
                    st.warning(f"Unknown qualification '{qualification}' for email {recipient_email}. Skipping.")
                    continue

                # Send the email using the SMTP settings
                if send_email(smtp_server, smtp_port, sender_email, sender_password, recipient_email, subject, message, attachment):
                    st.success(f"Email sent successfully to {recipient_email}")

                # Update progress bar and status
                progress.progress((index + 1) / total_emails)
                status_text.text(f"Sending email {index + 1} of {total_emails}: {recipient_email}")

                # Simulate a slight delay for smoother progress bar update
                time.sleep(0.5)

            # Remove sent emails from the DataFrame
            df = df.iloc[100:]  # Drop the first 100 rows

            # Save the updated contacts file back to Excel
            updated_file = "updated_contacts.xlsx"
            df.to_excel(updated_file, index=False)

            st.success("Processed emails and updated the contact file.")

            # Provide download link for updated file
            st.download_button(label="Download Updated Contacts File", data=open(updated_file, 'rb'), file_name=updated_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Include this page in your main function
def main():
    st.sidebar.title("Options")
    page = st.sidebar.radio("Select a page", ["Job Scraper 🇨🇦 👨🏻‍💻", "Email Scraper🇨🇦 ✉️", "SMTP 🇨🇦 📤"])
    if page == "Job Scraper 🇨🇦 👨🏻‍💻":
        page_1()
    elif page == "Email Scraper🇨🇦 ✉️":
        page_2()
    elif page == "SMTP 🇨🇦 📤":
        page_3()

if __name__ == "__main__":
    main()

