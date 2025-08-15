# core/scraping_manager.py
import asyncio
from playwright.async_api import async_playwright

from database.db_manager import db_manager
from database.models import Anime, Season, Episode, Genre, ContentType
from scrapers.jutsu_scraper import JutsuScraper
from scrapers.metadata_scraper import MetadataScraper

class ScrapingManager:
    def __init__(self):
        self.jutsu_scraper = JutsuScraper()
        self.metadata_scraper = MetadataScraper()

    async def _process_single_anime(self, anime_slug, browser):
        """
        Внутренний метод для полной обработки одного аниме с использованием
        существующего экземпляра браузера.
        """
        if db_manager.anime_exists(anime_slug):
            print(f"[INFO] Аниме '{anime_slug}' уже существует в базе данных. Пропуск.")
            return {"status": "skipped", "reason": "already exists"}

        print(f"[START] Начало обработки аниме: {anime_slug}")
        page = await browser.new_page()

        try:
            seasons_with_links = await self.jutsu_scraper.get_all_episode_links_for_anime(anime_slug, page)
            if not seasons_with_links:
                return {"status": "error", "reason": "failed to get episode links"}

            first_season_num = next(iter(seasons_with_links))
            first_episode_url = seasons_with_links[first_season_num][0]
            
            base_episode_data = await self.jutsu_scraper.parse_episode_page(first_episode_url, page, anime_slug)
            if not base_episode_data or base_episode_data.get('anime_title_rus') == "N/A":
                return {"status": "error", "reason": "failed to parse first episode to get title"}
            
            anime_title_rus = base_episode_data['anime_title_rus']
            metadata = await self.metadata_scraper.get_anime_details(anime_title_rus)

            with db_manager.session_scope() as session:
                content_type_name = (metadata.get('type') if metadata else 'Unknown') or 'Unknown'
                content_type_obj, _ = db_manager.get_or_create(session, ContentType, name=content_type_name)
                
                anime_obj = Anime(
                    slug=anime_slug, title_rus=anime_title_rus,
                    title_orig=metadata.get('title_orig') if metadata else None,
                    description_api=metadata.get('description_api') if metadata else None,
                    poster_url_api=metadata.get('poster_url_api') if metadata else None,
                    age_rating=metadata.get('age_rating') if metadata else None,
                    status=metadata.get('status') if metadata else None,
                    year=metadata.get('year') if metadata else None,
                    score=metadata.get('score') if metadata else None,
                    content_type_id=content_type_obj.id
                )
                session.add(anime_obj)

                if metadata and metadata.get('genres'):
                    for genre_name in metadata['genres']:
                        genre_obj, _ = db_manager.get_or_create(session, Genre, name=genre_name)
                        anime_obj.genres.append(genre_obj)
                
                session.flush()
                anime_id = anime_obj.id

                for season_num, episode_links in seasons_with_links.items():
                    season_obj, _ = db_manager.get_or_create(session, Season, anime_id=anime_id, season_number=season_num)
                    session.flush()
                    season_id = season_obj.id

                    for link in episode_links:
                        episode_data = base_episode_data if link == first_episode_url else await self.jutsu_scraper.parse_episode_page(link, page, anime_slug)
                        if episode_data:
                            ep = Episode(
                                anime_id=anime_id, season_id=season_id,
                                episode_number=episode_data.get('episode_number'),
                                title=episode_data.get('episode_title'),
                                source_url=episode_data.get('source_url'),
                                poster_local_path=episode_data.get('poster_local_path'),
                                duration_sec=episode_data.get('duration_sec'),
                                opening_start_sec=episode_data.get('opening_start_sec'),
                                opening_end_sec=episode_data.get('opening_end_sec'),
                                ending_start_sec=episode_data.get('ending_start_sec'),
                                ending_end_sec=episode_data.get('ending_end_sec'),
                                next_episode_url=episode_data.get('next_episode_url')
                            )
                            session.add(ep)
                        await asyncio.sleep(0.3)
            
            print(f"[SUCCESS] Аниме '{anime_slug}' успешно добавлено в базу данных.")
            return {"status": "success", "slug": anime_slug}
        
        finally:
            await page.close()

    async def add_specific_anime(self, anime_slug):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            result = await self._process_single_anime(anime_slug, browser)
            await browser.close()
        return result

    async def add_bulk_anime(self, limit: int):
        print(f"[START] Запуск массового добавления. Лимит: {limit}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            all_slugs_on_site = await self.jutsu_scraper.get_all_anime_slugs(page)
            await page.close()

            slugs_in_db = db_manager.get_all_anime_slugs()
            new_slugs = [slug for slug in all_slugs_on_site if slug not in slugs_in_db]
            
            if not new_slugs:
                print("[INFO] Новых аниме для добавления не найдено.")
                await browser.close()
                return {"status": "finished", "added_count": 0, "reason": "no new anime found"}

            slugs_to_add = new_slugs[:limit]
            print(f"[*] Найдено {len(new_slugs)} новых аниме. Будет обработано: {len(slugs_to_add)}")
            
            added_count = 0
            for slug in slugs_to_add:
                result = await self._process_single_anime(slug, browser)
                if result.get('status') == 'success':
                    added_count += 1
            
            await browser.close()
        
        return {"status": "finished", "added_count": added_count}

    async def run_continuous_scraping(self):
        print("[START] Запуск непрерывного скрапинга...")
        while True:
            print("\n" + "="*50)
            print(f"[{asyncio.get_event_loop().time()}] Новая итерация непрерывного скрапинга.")
            
            await self.add_bulk_anime(limit=10000)
            
            sleep_duration = 3600
            print(f"[*] Итерация завершена. Следующая проверка через {sleep_duration / 60:.0f} минут.")
            print("="*50 + "\n")
            await asyncio.sleep(sleep_duration)

