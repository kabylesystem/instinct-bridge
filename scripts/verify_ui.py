"""Browser checks and optional live synthetic transfer. Server must be running.
The launch URL is read from a private local file, never printed or persisted here.
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from instinct_bridge.authy import attach_authy, load_authy
from instinct_bridge.destination import brave_session, DELETE
from instinct_bridge.source import load_plan

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--launch-log', type=Path, required=True)
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
fixtures = root/'tests/fixtures'
artifacts = root/'docs/evidence'
artifacts.mkdir(parents=True, exist_ok=True)
url = re.search(r'http://127\.0\.0\.1:\d+/#\S+', args.launch_log.read_text()).group()
password = 'SYNTHETIC-export-password'
source = load_plan(fixtures/'bitwarden-pbkdf2-synthetic.json', password,
                   allow_partial=True, migration_names=True)
accounts = load_authy((fixtures/'authy-encrypted-synthetic.json').read_text(), password)
item = attach_authy(source.logins, accounts, {'synthetic-authy-1':0})[0]
report = {'checked_at':datetime.now(timezone.utc).isoformat(), 'data':'synthetic', 'iphone_capture_tested':False}
if args.live:
    with brave_session() as destination:
        assert not any(x['kind']=='login' and x['name'].casefold()==item.name.casefold() for x in destination.inventory()), 'Synthetic name already exists; test stopped without changes.'
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/brave', headless=True)
        context = browser.new_context(viewport={'width':1440,'height':1080})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda _: errors.append('JavaScript exception'))
        page.on('console', lambda message: errors.append('Browser console error') if message.type=='error' else None)
        page.goto(url,wait_until='networkidle')
        expect(page.locator('#preview')).to_be_disabled()
        assert not page.locator('#authy-option').evaluate('(element) => element.open')
        page.screenshot(path=str(artifacts/'desktop-load.png'),full_page=True)
        page.locator('#demo').click()
        expect(page.locator('#review')).to_be_visible()
        expect(page.locator('.authy-select')).to_have_value('0')
        assert page.locator('#connect').count()==0, 'Redundant connection action is still visible'
        page.screenshot(path=str(artifacts/'desktop-review.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(artifacts/'mobile-review.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
        page.locator('#clear').click()
        expect(page.locator('#sources')).to_be_visible()
        page.screenshot(path=str(artifacts/'mobile-load.png'),full_page=True)
        report.update(demo_pairing=True, demo_transfer_disabled=True, mobile_no_overflow=True)
        page.set_viewport_size({'width':1440,'height':1080})
        batch = {'encrypted':False,'items':[{'id':f'00000000-0000-4000-8000-{i:012d}',
            'type':1,'name':f'Synthetic account {i}','login':{'username':f'user-{i}@example.invalid',
            'password':'SYNTHETIC-demo-only'}} for i in range(1,463)]}
        page.locator('#bitwarden-file').set_input_files({'name':'synthetic-batch.json',
            'mimeType':'application/json','buffer':json.dumps(batch).encode()})
        expect(page.locator('#preview')).to_be_enabled()
        page.locator('#preview').click()
        expect(page.locator('#review')).to_be_visible()
        assert not page.locator('#accounts-details').evaluate('(element) => element.open')
        expect(page.locator('#transfer')).to_be_visible()
        page.screenshot(path=str(artifacts/'desktop-batch-review.png'),full_page=True)
        page.locator('#accounts-details > summary').click()
        page.locator('#account-search').fill('Synthetic account 417')
        assert page.locator('#account-rows tr:visible').count()==1, 'Search did not narrow the review list'
        visible_account = page.locator('#account-rows tr:visible .account-select')
        visible_account.uncheck()
        expect(page.locator('#selection-count')).to_have_text('461 accounts selected')
        expect(page.locator('#transfer-label')).to_have_text('Transfer 461 accounts')
        visible_account.check()
        expect(page.locator('#selection-count')).to_have_text('462 accounts selected')
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(artifacts/'mobile-batch-review.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile batch review overflows'
        page.locator('#clear').click()
        page.set_viewport_size({'width':1440,'height':1080})
        report['large_review_collapsed_and_searchable']=True
        page.locator('#bitwarden-file').set_input_files(fixtures/'bitwarden-pbkdf2-synthetic.json')
        page.locator('#authy-option > summary').click()
        page.locator('#authy-option .optional-content details > summary').click()
        page.locator('#authy-file').set_input_files(fixtures/'authy-encrypted-synthetic.json')
        page.locator('#bitwarden-password').fill(password)
        page.locator('#authy-password').fill(password)
        page.locator('#preview').click()
        expect(page.locator('#review')).to_be_visible()
        expect(page.locator('.authy-select')).to_have_value('0')
        expect(page.locator('#bitwarden-password')).to_have_value('')
        expect(page.locator('#authy-password')).to_have_value('')
        report['encrypted_upload_and_pairing']=True
        if args.live:
            # The single transfer click connects, then writes and verifies.
            page.locator('#transfer').click()
            expect(page.locator('#result-0')).to_have_text('Transferred & verified',timeout=90000)
            expect(page.locator('#transfer-progress')).to_be_visible()
            expect(page.locator('#transfer-meter')).to_have_attribute('value','1')
            report['single_transfer_click']=True
            report['live_transfer_verified']=True
            report['visible_progress']=True
            expect(page.locator('#transfer')).to_be_disabled()
            page.locator('#clear').click()
            page.locator('#bitwarden-file').set_input_files(fixtures/'bitwarden-pbkdf2-synthetic.json')
            if not page.locator('#authy-option').evaluate('(element) => element.open'):
                page.locator('#authy-option > summary').click()
            if not page.locator('#authy-option .optional-content details').evaluate('(element) => element.open'):
                page.locator('#authy-option .optional-content details > summary').click()
            page.locator('#authy-file').set_input_files(fixtures/'authy-encrypted-synthetic.json')
            page.locator('#bitwarden-password').fill(password)
            page.locator('#authy-password').fill(password)
            page.locator('#preview').click()
            expect(page.locator('#review')).to_be_visible()
            page.locator('#transfer').click()
            expect(page.locator('#result-0')).to_have_text('Already present · verified',timeout=60000)
            report['repeat_skipped_and_verified']=True
            page.screenshot(path=str(artifacts/'desktop-verified.png'),full_page=True)
        report['browser_errors']=errors
        assert not errors, 'Browser errors detected'
        browser.close()
finally:
    if args.live:
        with brave_session() as destination:
            checks = destination.verify(item)
            report['independent_readback']=checks
            if all(checks.values()):
                destination.call(DELETE,{'kind':'login','name':item.name})
            report['cleanup_verified']=not any(x['kind']=='login' and x['name']==item.name for x in destination.inventory())
    (artifacts/('2026-09-24-ui-e2e.json' if args.live else '2026-09-24-ui-browser.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
