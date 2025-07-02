import requests
import time
from typing import List, Dict, Optional
import json

class GoogleSearchAPI:
    def __init__(self, api_key: str, search_engine_id: str):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
    def search(self, query: str, num_results: int = 10, lang: str = 'it') -> List[Dict]:
        """
        Esegue una ricerca e restituisce i risultati
        
        Args:
            query: Termine di ricerca
            num_results: Numero di risultati (max 10 per richiesta)
            lang: Lingua dei risultati
        """
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'num': min(num_results, 10),  # Max 10 per richiesta
            'lr': f'lang_{lang}',
            'safe': 'medium'
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Estrai le informazioni essenziali
            results = []
            for item in data.get('items', []):
                result = {
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'display_link': item.get('displayLink', '')
                }
                results.append(result)
                
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"Errore nella richiesta: {e}")
            return []
        except KeyError as e:
            print(f"Errore nel parsing della risposta: {e}")
            return []

    def search_multiple_pages(self, query: str, total_results: int = 50) -> List[Dict]:
        """
        Cerca su più pagine per ottenere più risultati
        """
        all_results = []
        start_index = 1
        
        while len(all_results) < total_results:
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': query,
                'start': start_index,
                'num': 10
            }
            
            try:
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                items = data.get('items', [])
                if not items:  # Non ci sono più risultati
                    break
                    
                for item in items:
                    result = {
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'display_link': item.get('displayLink', '')
                    }
                    all_results.append(result)
                
                start_index += 10
                time.sleep(0.1)  # Pausa per rispettare i rate limits
                
            except requests.exceptions.RequestException as e:
                print(f"Errore nella richiesta: {e}")
                break
                
        return all_results[:total_results]

# Esempio di utilizzo
if __name__ == "__main__":
    # Sostituisci con le tue credenziali
    API_KEY = "la_tua_api_key"
    SEARCH_ENGINE_ID = "il_tuo_search_engine_id"
    
    google_search = GoogleSearchAPI(API_KEY, SEARCH_ENGINE_ID)
    
    # Ricerca semplice
    query = "intelligenza artificiale news 2024"
    results = google_search.search(query, num_results=5)
    
    print(f"Risultati per: {query}")
    print("-" * 50)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Snippet: {result['snippet']}")
        print()

# Classe per web scraping dei risultati
import requests
from bs4 import BeautifulSoup
import re

import requests
from bs4 import BeautifulSoup
import re
from typing import Optional

class WebScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def extract_content(self, url: str) -> Optional[str]:
        """
        Estrae il contenuto principale da una pagina web
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Rimuovi elementi non necessari
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'noscript']):
                element.decompose()

            # Possibili selettori per il contenuto principale
            selectors = [
                'main',
                'article',
                'section',
                'div[id*="content"]',
                'div[class*="content"]',
                'div[class*="main"]',
                'div[class*="article"]',
                'div[class*="post"]',
                'div[class*="text"]',
            ]

            main_content = None
            for selector in selectors:
                candidate = soup.select_one(selector)
                if candidate and len(candidate.get_text(strip=True)) > 200:
                    main_content = candidate
                    break
            
            # Fallback: div con più testo
            if not main_content:
                divs = soup.find_all('div')
                if divs:
                    main_content = max(divs, key=lambda d: len(d.get_text(strip=True)))

            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
                text = re.sub(r'\s+', ' ', text)
                return text[:5000]  # Limita a 5000 caratteri

            return None

        except Exception as e:
            print(f"Errore nel scraping di {url}: {e}")
            return None


# Integrazione completa
class WebResearchAssistant:
    def __init__(self, google_api_key: str="AIzaSyCaiQiqo_Tfxrr5gM0STv9guliP1enFIek", search_engine_id: str="20b44ba3cd1d745bf"):
        self.search_api = GoogleSearchAPI(google_api_key, search_engine_id)
        self.scraper = WebScraper()
    
    def research_topic(self, topic: str, num_sources: int = 5) -> Dict:
        """
        Ricerca completa su un topic
        """
        try:
            print(f"Ricerca in corso per: {topic}")
            
            # 1. Cerca risultati
            search_results = self.search_api.search(topic, num_sources)
            '''search_results = [
                {
                    "title": "How to make “cremina” for your homemade Italian espresso coffee ...",
                    "url": "https://wherethefoodiesgo.com/how-to-make-cremina-for-your-homemade-italian-espresso-coffee-and-a-few-rules-for-a-perfect-coffee-with-your-moka-pot/",
                    "content": "How do I make a homemade espresso with la cremina , like the one they serve you at the bar? Extremely easy! Put some sugar in a glass (or cup or wherever it’s easy for you to stir!); When the coffee comes out of the moka pot (we call it the “first” coffee), pour a few drops in the sugar; then stir with a teaspoon until it gets like a yellowish cream; …and your cremina is ready! Now put it in your homemade espresso coffee…and enjoy! 😉 Do you know the simple rules to make a good moka pot coffee? 1. Don’t put to much coffee powder in the pot and don’t press! 2. Turn off the burner as soon as watery coffee starts to come out (when the coffee coming out is not sticking to the sides of the “tower” anymore)! 3. Never wash your moka pot with soap! Do you want to surprise your friends and make a lemon flavoured coffee ? CLICK HERE to learn how to make it! Copyright © Where The Foodies Go. All Rights Reserved. Liked it? Share it! Click to share on Facebook (Opens in new window) Facebook Click to share on Pinterest (Opens in new window) Pinterest Click to share on X (Opens in new window) X Click to share on WhatsApp (Opens in new window) WhatsApp More Click to share on LinkedIn (Opens in new window) LinkedIn Click to share on Reddit (Opens in new window) Reddit Click to share on Tumblr (Opens in new window) Tumblr Click to email a link to a friend (Opens in new window) Email Like this: Like Loading... 10 comments Amazing.Really appreciated your article and also inspiring on How to make “cremina” for your homemade Italian espresso coffee! (and a few rules for a perfect coffee with your moka pot). Loading... Reply We’re really happy you appreciated it! Thank you for stopping by our blog! 😊 Loading... Reply Fantastic! I have always wanted to know how to make this, keep up the good work 🙂 Loading... Reply We’re happy to help! 😉 Thank you for stopping by! Loading... Reply Yes yes oh yes. I love coffee, love “Cremina” and the coffee shops that serve coffee that way. Thank you. Mystery solved. :0) Loading... Reply I’m “cremina” addicted! 😉 Very nice to meet you! Alessia Loading... Reply one more tip I’ve learned from my Italian friends…gently stir the coffee with a small spoon around the center post before pouring Loading... Reply my heart accelerates just reading the “how to” Loading... Reply Molto ben spiegato il metodo, miei complimenti Loading... Reply Grazie! 🙂 Loading... Reply Leave a Reply Cancel reply This site uses Akismet to reduce spam. Learn how your comment data is processed.",
                    "snippet": "Sep 7, 2014 ... Do you know the simple rules to make a good moka pot coffee? 1. Don't put to much coffee powder in the pot and don't press! 2. Turn off the ..."
                }
            ]'''
            
            # 2. Scraping dei contenuti
            scraped_content = []
            for result in search_results:
                print(f"Scraping: {result['url']}")
                content = self.scraper.extract_content(result['url'])
                if content:
                    scraped_content.append({
                        'title': result['title'],
                        'url': result['url'],
                        'content': content,
                        'snippet': result['snippet']
                    })
            
            #save everything to a file
            with open(f"{topic}_research.json", "w", encoding="utf-8") as f:
                json.dump(scraped_content, f, ensure_ascii=False, indent=4)
            
            return {
                'topic': topic,
                'sources': scraped_content,
                'total_sources': len(scraped_content)
            }
        except Exception as e:
            print(f"Errore nella ricerca del topic '{topic}': {e}")
            return {
                'topic': topic,
                'sources': [],
                'total_sources': 0,
                'error': str(e)
            }