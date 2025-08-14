# scrapers/metadata_scraper.py
import asyncio
import aiohttp
import config

class MetadataScraper:
    """
    Получает расширенные метаданные об аниме из Jikan API.
    """
    def __init__(self):
        self.api_url = config.JIKAN_API_URL

    async def get_anime_details(self, anime_title_rus):
        """
        Ищет аниме по русскому названию и возвращает детальную информацию.
        """
        print(f"[*] Поиск метаданных для '{anime_title_rus}' в Jikan API...")
        search_url = f"{self.api_url}/anime"
        params = {'q': anime_title_rus, 'limit': 1}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=params, timeout=10) as response:
                    if response.status != 200:
                        print(f"  [!] Jikan API вернул статус {response.status}")
                        return None
                    
                    search_results = await response.json()
                    if not search_results.get('data'):
                        print(f"  [!] Аниме '{anime_title_rus}' не найдено в Jikan API.")
                        return None

                    anime_data = search_results['data'][0]
                    print(f"  [+] Найдено: {anime_data.get('title')}")

                    return {
                        'title_orig': anime_data.get('title_japanese'),
                        'description_api': anime_data.get('synopsis'),
                        'poster_url_api': anime_data.get('images', {}).get('jpg', {}).get('large_image_url'),
                        'age_rating': anime_data.get('rating'),
                        'status': anime_data.get('status'),
                        'year': anime_data.get('year'),
                        'score': anime_data.get('score'),
                        'type': anime_data.get('type'),
                        'genres': [genre['name'] for genre in anime_data.get('genres', [])]
                    }
        except Exception as e:
            print(f"  [!] Ошибка при работе с Jikan API: {e}")
            return None
        finally:
            await asyncio.sleep(1) # Соблюдаем rate limit Jikan API

