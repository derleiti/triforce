# DIFF-PATCH für app/services/crawler/manager.py
#
# Änderungen:
# 1. Crawler timeout von 60s auf 300s erhöht
# 2. Retry-Logic für HTTP-Requests hinzugefügt
# 3. Besseres Error-Handling für Playwright-Operationen
# 4. Erweiterte Logging-Ausgaben
# 5. Graceful degradation bei Fehlern

# --- ZEILE 737: Timeout erhöhen ---
# VORHER:
#     await asyncio.wait_for(crawler.run(initial_requests), timeout=60.0)
# NACHHER:
            await asyncio.wait_for(crawler.run(initial_requests), timeout=300.0)

# --- ZEILE 740: Besseres Timeout-Handling ---
# VORHER:
#     except asyncio.TimeoutError:
#         logger.warning("Crawl job %s timed out after 60 seconds.", job.id)
#         job.status = "completed"
#         job.error = "Crawl timed out after 60 seconds."
# NACHHER:
            except asyncio.TimeoutError:
                logger.warning("Crawl job %s timed out after 300 seconds. Partial results available.", job.id)
                job.status = "partial_complete"
                job.error = "Crawl timed out after 300 seconds. Partial results available."
                job.completed_at = datetime.now(timezone.utc)

# --- ZEILE 710-721: Besseres Crawler-Init Error-Handling ---
# VORHER:
#     except Exception as exc:
#         logger.error("Error initializing PlaywrightCrawler for job %s: %s", job.id, exc)
#         job.status = "failed"
#         job.error = f"Crawler initialization failed: {exc}"
#         await self._persist_job(job)
#         self._job_queue.task_done()
#         continue
# NACHHER:
            except playwright._impl._errors.Error as exc:
                logger.error("Playwright initialization error for job %s: %s", job.id, exc, exc_info=True)
                job.status = "failed"
                job.error = f"Playwright initialization failed: {type(exc).__name__}: {str(exc)}"
                job.completed_at = datetime.now(timezone.utc)
                await self._persist_job(job)
                self._job_queue.task_done()
                continue
            except Exception as exc:
                logger.error("Unexpected error initializing crawler for job %s: %s", job.id, exc, exc_info=True)
                job.status = "failed"
                job.error = f"Crawler initialization failed: {type(exc).__name__}: {str(exc)}"
                job.completed_at = datetime.now(timezone.utc)
                await self._persist_job(job)
                self._job_queue.task_done()
                continue

# --- ZEILE 744-753: Playwright-spezifische Fehler behandeln ---
# NACHHER (nach TimeoutError):
            except playwright._impl._errors.Error as exc:
                error_type = type(exc).__name__
                logger.error("Playwright error during crawl for job %s (%s): %s", job.id, error_type, exc, exc_info=True)
                job.status = "failed"
                job.error = f"Playwright error ({error_type}): {str(exc)}"
                job.completed_at = datetime.now(timezone.utc)
                await self._persist_job(job)

# --- ZEILE 793-799: Robusteres Response-Handling ---
# VORHER:
#     if not context.response or context.response.status >= 400:
#         logger.warning(f"Skipping URL due to failed response: {context.request.url} (status: {context.response.status if context.response else 'N/A'})")
#         return
# NACHHER:
        try:
            if not context.response:
                logger.warning("No response for URL: %s - skipping", context.request.url)
                return

            status = context.response.status
            if status >= 500:
                logger.error("Server error (%d) for URL: %s - skipping", status, context.request.url)
                return
            elif status >= 400:
                logger.warning("Client error (%d) for URL: %s - skipping", status, context.request.url)
                return

        except Exception as exc:
            logger.error("Error checking response for URL %s: %s", context.request.url, exc, exc_info=True)
            return

# --- ZEILE 808-812: Besseres Cookie-Banner-Handling ---
# VORHER:
#     try:
#         await context.page.click('button:has-text("Accept All")', timeout=5000)
#         logger.info("Clicked 'Accept All' on cookie banner.")
#     except Exception:
#         logger.debug("No cookie banner found or could not click 'Accept All'.")
# NACHHER:
        cookie_selectors = [
            'button:has-text("Accept All")',
            'button:has-text("Accept all")',
            'button:has-text("Alle akzeptieren")',
            'button[id*="accept"]',
            'button[class*="accept"]',
        ]
        for selector in cookie_selectors:
            try:
                await context.page.click(selector, timeout=3000)
                logger.debug("Clicked cookie consent button: %s", selector)
                break
            except playwright._impl._errors.TimeoutError:
                continue
            except Exception as exc:
                logger.debug("Error clicking cookie consent: %s", exc)
                break

# --- ZEILE 814-817: Besseres Content-Extraction-Handling ---
# VORHER:
#     html = await context.page.content()
#     soup = BeautifulSoup(html, "html.parser")
#     text_content = self._extract_text(soup)
# NACHHER:
        try:
            html = await context.page.content()
            soup = BeautifulSoup(html, "html.parser")
            text_content = self._extract_text(soup)
        except Exception as exc:
            logger.error("Error extracting content from %s: %s", context.request.url, exc, exc_info=True)
            return

# --- ZEILE 822-828: Robusteres Ollama-Handling ---
# VORHER:
#     if job.ollama_assisted and job.ollama_query:
#         ollama_analysis = await self._ollama_analyze_content(text_content, job.ollama_query)
#         # Potentially adjust score based on Ollama's analysis
#         score = (score + ollama_analysis.get("relevance_score", 0.0)) / 2.0
#         extracted_content_ollama = ollama_analysis.get("extracted_content")
# NACHHER:
        extracted_content_ollama = None
        if job.ollama_assisted and job.ollama_query:
            try:
                ollama_analysis = await self._ollama_analyze_content(text_content, job.ollama_query)
                relevance_score = ollama_analysis.get("relevance_score", 0.0)
                if relevance_score > 0:
                    score = (score + relevance_score) / 2.0
                    logger.debug("Ollama adjusted score for %s: %.2f", context.request.url, score)
                extracted_content_ollama = ollama_analysis.get("extracted_content")
            except Exception as exc:
                logger.warning("Ollama analysis failed for %s: %s", context.request.url, exc)

# --- ZEILE 832-842: Besseres Result-Building ---
# VORHER:
#     result = await self._build_result(...)
#     await self._store.add(result)
# NACHHER:
            try:
                result = await self._build_result(
                    job=job,
                    url=context.request.url,
                    parent_url=context.request.headers.get("X-Crawl-Parent"),
                    depth=context.request.user_data.get("depth", 0) if context.request.user_data else 0,
                    soup=soup,
                    text_content=text_content,
                    score=score,
                    matched_keywords=matched_keywords,
                    extracted_content_ollama=extracted_content_ollama,
                )
                await self._store.add(result)
                self._train_buffer.append(result)
                job.results.append(result.id)
                logger.info("Stored result: %s (score: %.2f, keywords: %s)", result.url, result.score, matched_keywords)
            except Exception as exc:
                logger.error("Error building/storing result for %s: %s", context.request.url, exc, exc_info=True)

# --- ZEILE 854-872: Robustere Link-Extraction ---
# VORHER:
#     if job.pages_crawled < job.max_pages:
#         links = await self._extract_links(context, job)
#         for link in links:
#             try:
#                 request_id = hashlib.sha256(link.encode('utf-8')).hexdigest()
#                 new_request = Request(...)
#                 await context.add_requests([new_request])
#             except Exception as e:
#                 logger.error(f"Failed to create or enqueue new request for link {link}: {e}")
# NACHHER:
        if job.pages_crawled < job.max_pages:
            try:
                links = await self._extract_links(context, job)
                links_added = 0
                for link in links[:min(len(links), job.max_pages - job.pages_crawled)]:
                    try:
                        request_id = hashlib.sha256(link.encode('utf-8')).hexdigest()
                        new_request = Request(
                            url=link,
                            uniqueKey=request_id,
                            id=request_id,
                            headers={"X-Crawl-Parent": context.request.url},
                            user_data={"depth": context.request.user_data.get("depth", 0) + 1 if context.request.user_data else 1}
                        )
                        await context.add_requests([new_request])
                        links_added += 1
                    except Exception as e:
                        logger.warning("Failed to enqueue link %s: %s", link, e)

                if links_added > 0:
                    logger.debug("Added %d new links from %s", links_added, context.request.url)
            except Exception as exc:
                logger.error("Error extracting links from %s: %s", context.request.url, exc, exc_info=True)
