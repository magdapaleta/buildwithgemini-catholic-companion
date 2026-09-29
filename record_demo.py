import asyncio
import os
import subprocess
from playwright.async_api import async_playwright

async def run():
    print("Launching Chromium via Playwright...")
    async with async_playwright() as p:
        # Launch browser with video recording enabled
        video_dir = "/config/Desktop/BuildWithGemini/catholic-companion/demo_recordings"
        os.makedirs(video_dir, exist_ok=True)
        
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            record_video_dir=video_dir,
            record_video_size={"width": 1400, "height": 900}
        )
        
        page = await context.new_page()
        
        print("Navigating to http://localhost:8080 ...")
        await page.goto("http://localhost:8080", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # 1. Showcase the App Overview & Daily Feast Dashboard
        print("Showcasing dashboard...")
        await page.wait_for_timeout(1500)
        
        # Scroll right dashboard gently to show features
        dashboard = await page.query_selector("#main-content")
        if dashboard:
            await dashboard.evaluate("(el) => el.scrollTo({ top: 350, behavior: 'smooth' })")
            await page.wait_for_timeout(1800)
            await dashboard.evaluate("(el) => el.scrollTo({ top: 0, behavior: 'smooth' })")
            await page.wait_for_timeout(1500)
            
        # 2. PROMPT 1: What the app does best - Spiritual companionship, daily Gospel & Liturgical feast
        prompt1 = "Hello Oiramen, my name is Gabriel. Today is the Feast of the Archangels. Can you share today's Gospel and reflection with me?"
        print(f"Typing Prompt 1: {prompt1}")
        
        input_el = await page.query_selector("#input")
        send_btn = await page.query_selector("#send-button")
        
        await input_el.type(prompt1, delay=35)
        await page.wait_for_timeout(800)
        await send_btn.click()
        
        # Wait for agent reply to appear in log
        print("Waiting for Oiramen reply 1...")
        await page.wait_for_selector(".msg-row.agent:nth-of-type(2)", timeout=35000)
        await page.wait_for_timeout(4000)
        
        # 3. PROMPT 2: Richer prompt showing tool calls, database lookup / Firestore persistence, and prayer card generation
        prompt2 = "I am nervous about an important medical exam this Friday, October 2nd. Could you save this prayer intention and pray for me?"
        print(f"Typing Prompt 2: {prompt2}")
        
        await input_el.type(prompt2, delay=35)
        await page.wait_for_timeout(800)
        await send_btn.click()
        
        print("Waiting for Oiramen reply 2 (with generated Prayer Card & Firestore persistence)...")
        await page.wait_for_selector(".msg-row.agent:nth-of-type(3)", timeout=35000)
        await page.wait_for_timeout(3500)
        
        # Highlight generated prayer card image
        card_img = await page.query_selector(".prayer-card-wrapper img")
        if card_img:
            await card_img.scroll_into_view_if_needed()
            await page.wait_for_timeout(2500)
            
        # Jump to Section 3 in Dashboard using the new left navigation tabs to show the intention persisted in Firestore!
        print("Clicking 'Your Intentions' tab to show Firestore database persistence...")
        intentions_tab = await page.query_selector(".nav-pill:nth-child(3)")
        if intentions_tab:
            await intentions_tab.click()
            await page.wait_for_timeout(3000)
            
        print("Finishing demo recording...")
        await page.wait_for_timeout(2000)
        
        # Close context to flush video
        await context.close()
        await browser.close()
        
        # Find generated video
        files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith(".webm")]
        latest_video = max(files, key=os.path.getmtime)
        print(f"Raw video saved at: {latest_video}")
        return latest_video

video_path = asyncio.run(run())

# Merge with lo-fi background music using ffmpeg
final_mp4 = "/config/Desktop/BuildWithGemini/catholic-companion/oiramen_agent_demo.mp4"
print("Merging video and upbeat lo-fi audio...")
cmd = [
    "ffmpeg", "-y",
    "-i", video_path,
    "-i", "lofi_track.wav",
    "-filter_complex", "[1:a]volume=0.35[a]",
    "-map", "0:v",
    "-map", "[a]",
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "22",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    final_mp4
]
subprocess.run(cmd, check=True)
print(f"Successfully produced final demo video with upbeat lo-fi background music: {final_mp4}")
