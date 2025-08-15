# scrapers/jutsu_scraper.py
import asyncio
import re
import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import aiohttp
import config

class JutsuScraper:
    """
    Скрапер для jut.su. Использует Playwright для всех взаимодействий,
    чтобы избежать блокировок по IP и обходить защиту Cloudflare.
    """
    def __init__(self):
        self.base_url = config.JUTSU_BASE_URL
        self.output_dir = config.POSTERS_OUTPUT_DIR

    async def get_all_anime_slugs(self, page):
        """
        Собирает слaги всех аниме с сайта, проходя по всем страницам каталога
        с использованием Playwright.
        """
        all_slugs = set()
        page_num = 1
        while True:
            catalog_url = f"{self.base_url}/anime/"
            if page_num > 1:
                catalog_url = f"{self.base_url}/anime/page-{page_num}/"
            
            print(f"[*] Анализ каталога: {catalog_url}")
            try:
                await page.goto(catalog_url, timeout=30000, wait_until='domcontentloaded')
                
                # Проверяем, не перенаправило ли нас на главную (признак конца страниц)
                if page_num > 1 and "page" not in page.url:
                    print(f"[*] Достигнут конец каталога (перенаправление на главную).")
                    break

                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Используем более надежный селектор
                links = soup.select('div.all_anime_global > a')
                if not links:
                    print(f"[*] На странице {page_num} не найдено ссылок на аниме. Завершение.")
                    break

                page_slugs = set()
                for link in links:
                    href = link.get('href')
                    if href and href.startswith('/') and not href.startswith(('/user/', '/news/')):
                        slug = href.strip('/').split('/')[-1]
                        page_slugs.add(slug)
                
                if not page_slugs:
                    print(f"[*] На странице {page_num} не найдено подходящих слагов. Завершение.")
                    break
                
                all_slugs.update(page_slugs)
                print(f"  [+] Найдено {len(page_slugs)} аниме. Всего уникальных: {len(all_slugs)}")
                page_num += 1
                await asyncio.sleep(1) # Задержка между страницами

            except Exception as e:
                print(f"  [!] Ошибка при доступе к каталогу {catalog_url}: {e}")
                break
        
        return list(all_slugs)

    async def get_all_episode_links_for_anime(self, anime_slug, page):
        """Собирает все ссылки на эпизоды и сезоны для конкретного аниме."""
        anime_page_url = f"{self.base_url}/{anime_slug}/"
        print(f"[*] Анализ страницы аниме '{anime_slug}'...")
        seasons = {}
        try:
            await page.goto(anime_page_url, timeout=30000, wait_until='domcontentloaded')
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            season_tabs = soup.select('.the_season_tabs a')
            if season_tabs:
                for tab in season_tabs:
                    season_title = tab.get_text(strip=True)
                    season_match = re.search(r'(\d+)\s*сезон', season_title, re.IGNORECASE)
                    season_number = int(season_match.group(1)) if season_match else 1
                    
                    season_content_id = tab['href'].replace('#', '')
                    season_content = soup.find(id=season_content_id)
                    if season_content:
                        episode_links = [urljoin(self.base_url, a['href']) for a in season_content.select('a[href*="episode-"]')]
                        seasons[season_number] = sorted(episode_links, key=lambda x: int(re.search(r'episode-(\d+)', x).group(1)))
            else:
                episode_links = [urljoin(self.base_url, a['href']) for a in soup.select('a[href*="episode-"]')]
                if episode_links:
                     seasons[1] = sorted(episode_links, key=lambda x: int(re.search(r'episode-(\d+)', x).group(1)))
            
            print(f"  [+] Найдено {len(seasons)} сезонов и {sum(len(v) for v in seasons.values())} эпизодов.")
            return seasons

        except Exception as e:
            print(f"  [!] Ошибка при доступе к странице аниме {anime_page_url}: {e}")
            return {}

    async def parse_episode_page(self, episode_url, page, anime_slug):
        """Парсит страницу эпизода для получения метаданных."""
        print(f"  [*] Парсинг данных: {episode_url}")
        try:
            await page.goto(episode_url, timeout=20000, wait_until='networkidle')
        except Exception as e:
            print(f"    [!] Ошибка загрузки страницы эпизода: {e}")
            return None
        
        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        data = {'source_url': episode_url}

        match_ep = re.search(r'episode-(\d+)', episode_url)
        data['episode_number'] = int(match_ep.group(1)) if match_ep else 0

        h1_title = soup.select_one('h1.header_video')
        data['anime_title_rus'] = h1_title.get_text(strip=True).replace('Смотреть ', '').rsplit(' ', 2)[0] if h1_title else "N/A"
        
        episode_h2 = soup.select_one('h2.video_plate_title')
        data['episode_title'] = episode_h2.get_text(strip=True) if episode_h2 else "N/A"
        
        try:
            window_vars = await page.evaluate("""() => {
                const data = {};
                const keys = [
                    'video_duration', 'this_video_duration', 
                    'video_intro_start', 'video_intro_end',
                    'video_outro_start', 'video_outro_end',
                    'next_episode_link'
                ];
                keys.forEach(key => {
                    if (typeof window[key] !== 'undefined') {
                        data[key] = window[key];
                    }
                });
                return data;
            }""")
        except Exception as e:
            print(f"    [!] Не удалось извлечь window переменные: {e}")
            window_vars = {}

        data['duration_sec'] = window_vars.get('video_duration') or window_vars.get('this_video_duration')
        data['opening_start_sec'] = window_vars.get('video_intro_start')
        data['opening_end_sec'] = window_vars.get('video_intro_end')
        data['ending_start_sec'] = window_vars.get('video_outro_start')
        data['ending_end_sec'] = window_vars.get('video_outro_end')
        next_link = window_vars.get('next_episode_link')
        data['next_episode_url'] = urljoin(self.base_url, next_link) if next_link and isinstance(next_link, str) else None

        poster_url = soup.select_one('meta[property="og:image"]')['content'] if soup.select_one('meta[property="og:image"]') else None
        if poster_url:
            poster_path = os.path.join(self.output_dir, anime_slug, f"episode_{data['episode_number']}_poster.jpg")
            if await self._download_image(poster_url, poster_path):
                data['poster_local_path'] = poster_path

        return data

    async def _download_image(self, url, save_path):
        """Асинхронно скачивает изображение."""
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    response.raise_for_status()
                    with open(save_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
            return True
        except Exception as e:
            print(f"      [!] Ошибка скачивания {url}: {e}")
            return False
