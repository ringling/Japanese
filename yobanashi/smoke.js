// Smoke test: every story in stories/index.json opens in the reader without page errors.
const { chromium } = require('../.playwright/node_modules/playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const port = 8700 + Math.floor(Math.random() * 90);
const srv = spawn('python3', ['-m', 'http.server', String(port)], { cwd: root, stdio: 'ignore' });

(async () => {
  await new Promise(r => setTimeout(r, 800));
  const index = JSON.parse(fs.readFileSync(path.join(__dirname, 'stories', 'index.json'), 'utf8'));
  const browser = await chromium.launch();
  let failed = 0;
  for (const s of index) {
    const page = await browser.newPage();
    const errs = [];
    page.on('pageerror', e => errs.push(e.message));
    page.on('requestfailed', r => { if (r.url().startsWith(`http://localhost:${port}`)) errs.push('request failed: ' + r.url()); });
    await page.goto(`http://localhost:${port}/yobanashi/`);
    await page.evaluate(id => localStorage.setItem('yobanashi.v3', JSON.stringify({ storyId: id, pos: 1 })), s.id);
    await page.reload();
    await page.waitForSelector('#slide .ja', { timeout: 8000 }).catch(() => errs.push('slide did not render'));
    const count = await page.locator('#count').innerText().catch(() => '');
    if (count !== `2 / ${s.lines}`) errs.push(`count "${count}" != "2 / ${s.lines}"`);
    if (!(await page.locator('#slide ruby').count()) && s.words) errs.push('no furigana on slide 2');
    if (s.words) {
      await page.keyboard.press('w');
      const n = await page.locator('.wcell').count();
      if (n !== s.words) errs.push(`words overlay has ${n}, index says ${s.words}`);
    }
    if (s.audio && !(await page.locator('#tAudio').isVisible())) errs.push('audio button hidden although story has timestamps');
    console.log(`${errs.length ? 'FAIL' : 'ok  '} ${s.id} ${s.title}${errs.length ? '\n     ' + errs.join('\n     ') : ''}`);
    failed += errs.length ? 1 : 0;
    await page.close();
  }
  await browser.close();
  srv.kill();
  process.exit(failed ? 1 : 0);
})();
