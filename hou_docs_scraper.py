import os
import re
import sys
import time
import logging

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logging.basicConfig(level="INFO", format="[%(levelname)s] - %(message)s")
log = logging.getLogger(__name__)

START_URL = "http://127.0.0.1:48626/hom/hou/index.html"

class DocumentationScraper:
    def __init__(self, start_url, output_dir="scraped_docs", delay=1):
        """
        Initialize the scraper with a starting URL and output directory.
        
        Args:
            start_url (str): The URL to start scraping from
            output_dir (str): Directory to save scraped content
            delay (float): Time to wait between requests (in seconds)
        """
        self.start_url = start_url
        self.base_url = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"
        self.output_dir = output_dir
        self.delay = delay
        self.visited_urls = set()
        self.to_visit = [start_url]
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def get_filename_from_url(self, url):
        """Convert URL to a valid filename"""
        # Remove query parameters and fragments
        url = url.split("?")[0].split("#")[0]
        
        # Get the last part of the URL path
        log.debug(f"URL: {url}")

        filename = url.replace(self.base_url, "")
        filename = filename.replace("/", "_")

        # If filename is empty (URL ends with /), use the domain name
        if not filename:
            filename = urlparse(url).netloc
        
        # Replace invalid filename characters
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # If filename doesn't end with .html, add it
        if not filename.endswith(".html"):
            filename += ".html"

        # Remove leading underscores
        filename = filename.lstrip("_")

        log.debug(f"Filename: {filename}")
            
        return filename

    def process_html_content(self, url, html_content):
        """
        Process HTML content to:
        1. Replace documentation links with local file paths
        2. Remove non-documentation links
        """
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Process all anchor tags
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute_url = urljoin(url, href)
            
            # Handle fragments (anchors within the same page)
            if "#" in absolute_url:
                base_url = absolute_url.split("#")[0]
                fragment = absolute_url.split("#")[1]
                
                # If base URL is a doc page, replace with local link + fragment
                if self.is_documentation_page(base_url):
                    local_filename = self.get_filename_from_url(base_url)
                    a_tag["href"] = f"{local_filename}#{fragment}"
                # If it"s a fragment in the current page, keep it as is
                elif base_url == url:
                    a_tag["href"] = f"#{fragment}"
                # Otherwise, remove the link but keep the text
                else:
                    a_tag.replace_with(a_tag.text)
            # Handle regular links
            else:
                # If it's a documentation page we've visited, replace with local path
                if self.is_documentation_page(absolute_url):
                    local_filename = self.get_filename_from_url(absolute_url)
                    a_tag["href"] = local_filename
                # Otherwise, remove the link but keep the text
                else:
                    a_tag.replace_with(a_tag.text)
        
        return str(soup)
    
    def save_content(self, url, content):
        """Save the content to a file"""
        # Process the HTML content to handle links
        processed_content = self.process_html_content(url, content)
        
        filename = self.get_filename_from_url(url)
        file_path = os.path.join(self.output_dir, filename)

        if os.path.exists(file_path):
            log.warning(f"File already exists: {file_path}")
        
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(processed_content)
            
        log.info(f"Saved: {url} -> {file_path}")
    
    def get_page_content(self, url):
        """Fetch and return page content"""
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Documentation Scraper)"})
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_links(self, url, html_content):
        """Extract links from the HTML content that are part of the documentation"""
        soup = BeautifulSoup(html_content, "html.parser")
        links = []
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute_url = urljoin(url, href)
            
            # Only follow links to the same domain and avoid external links
            if absolute_url.startswith(self.base_url) and "#" not in absolute_url:
                links.append(absolute_url)
                
        return links
    
    def is_documentation_page(self, url):
        """
        Determine if the page is part of the documentation.
        This is a basic implementation that you might need to customize.
        """
        # Check URL pattern (modify this based on the documentation structure)
        return False if not url.startswith(START_URL.replace("index.html", "")) else True
    
    def scrape(self, max_pages=None):
        """
        Scrape the documentation starting from the initial URL.
        
        Args:
            max_pages: Maximum number of pages to scrape (None for unlimited)
        """
        page_count = 0
        
        while self.to_visit and (max_pages is None or page_count < max_pages):
            log.info(f"Pages scraped: {page_count}")

            # Get the next URL to visit
            current_url = self.to_visit.pop(0)
            
            # Skip if already visited
            if current_url in self.visited_urls:
                continue
                
            log.info(f"Scraping: {current_url}")
            
            # Mark as visited
            self.visited_urls.add(current_url)
            
            # Get the page content
            html_content = self.get_page_content(current_url)
            if not html_content:
                continue
                
            # Check if it's a documentation page
            if self.is_documentation_page(current_url):
                log.info("Start")
                # Save the content
                self.save_content(current_url, html_content)
                page_count += 1
                
                # Extract links from the page
                links = self.extract_links(current_url, html_content)
                
                # Add new links to the to_visit list
                for link in links:
                    if link not in self.visited_urls and link not in self.to_visit:
                        self.to_visit.append(link)
                
                log.info("End")
                print("\n")
            
            # Respect the delay between requests
            time.sleep(self.delay)
            
        log.info(f"Scraping complete. Scraped {page_count} pages.")

# Example usage
if __name__ == "__main__":
    # Replace with the URL of the documentation you want to scrape
    
    
    scraper = DocumentationScraper(
        start_url=START_URL,
        output_dir="scraped_documentation",
        delay=0  # Be nice to the server: 2 seconds between requests
    )
    
    # Start scraping (limit to 100 pages)
    scraper.scrape(max_pages=10000)
