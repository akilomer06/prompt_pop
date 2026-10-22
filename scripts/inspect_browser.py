from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path('test-results');out.mkdir(exist_ok=True)
lines=Path('local-access.txt').read_text(encoding='utf-8-sig').splitlines()
username=lines[0].split(': ',1)[1]
password=lines[1].split(': ',1)[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    errors=[]
    page.on('pageerror',lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8000')
    page.wait_for_load_state('networkidle')
    page.screenshot(path=str(out/'login-desktop.png'),full_page=True)
    print('Login form labels:',page.locator('label').all_text_contents())
    page.get_by_label('Account',exact=True).fill(username)
    page.get_by_label('Access code',exact=True).fill(password)
    page.get_by_role('button',name='Enter the competition').click()
    page.get_by_role('heading',name='Control room',exact=True).wait_for()
    page.wait_for_load_state('networkidle')
    page.screenshot(path=str(out/'control-desktop.png'),full_page=True)
    print('Navigation:',page.locator('nav button').all_text_contents())
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(out/'control-mobile.png'),full_page=True)
    print('Horizontal overflow:',page.evaluate('document.documentElement.scrollWidth > innerWidth'))
    print('Browser errors:',errors)
    browser.close()
