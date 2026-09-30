/**
 * 名刺スキャナー
 * スマホのカメラで名刺を撮影 → Google ドライブの無料OCRで読み取り → 確認・修正 → スプレッドシートに追記。
 * 「対応者」列には常に RESPONDER（多良）を記入する。
 */

const SPREADSHEET_ID = '1jApTwQmymraPikdQAngU0UCyxiYi7L1bQZr9tRTzQHw';
const SHEET_NAME = ''; // 空なら先頭のシートに追記
const RESPONDER = '多良';

// 読み取り項目と、スプレッドシートの見出しとして認識する名前の候補
const FIELDS = [
  { key: 'company',    label: '会社名',   aliases: ['会社名', '会社', '企業名', '法人名', '団体名', '所属', 'company'] },
  { key: 'department', label: '部署',     aliases: ['部署', '部署名', '部門', '所属部署', 'department'] },
  { key: 'title',      label: '役職',     aliases: ['役職', '肩書', '肩書き', 'title'] },
  { key: 'name',       label: '氏名',     aliases: ['氏名', '名前', '担当者', '担当者名', 'name'] },
  { key: 'name_kana',  label: 'ふりがな', aliases: ['ふりがな', 'フリガナ', 'よみがな', 'カナ'] },
  { key: 'email',      label: 'メール',   aliases: ['メール', 'メールアドレス', 'mail', 'e-mail', 'email'] },
  { key: 'phone',      label: '電話',     aliases: ['電話', '電話番号', 'tel', '代表電話'] },
  { key: 'mobile',     label: '携帯',     aliases: ['携帯', '携帯番号', '携帯電話', 'mobile'] },
  { key: 'fax',        label: 'FAX',      aliases: ['fax', 'ファックス'] },
  { key: 'postal',     label: '郵便番号', aliases: ['郵便番号', '〒', 'zip'] },
  { key: 'address',    label: '住所',     aliases: ['住所', '所在地', 'address'] },
  { key: 'url',        label: 'URL',      aliases: ['url', 'hp', 'ホームページ', '会社web', 'webサイト', 'web', 'サイト'] },
  { key: 'memo',       label: 'メモ',     aliases: ['メモ', '備考', 'note'] },
];
const RESPONDER_ALIASES = ['対応者', '対応', '営業担当'];
const DATE_ALIASES = ['対応日', '日付', '登録日', '取得日', '交換日', '受付日', '日時', 'date'];

function doGet() {
  const t = HtmlService.createTemplateFromFile('index');
  t.fields = FIELDS.map(f => ({ key: f.key, label: f.label }));
  t.responder = RESPONDER;
  return t.evaluate()
    .setTitle('名刺スキャナー')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/** 画像（base64 JPEG）から名刺の項目を読み取る（Google ドライブの無料OCRを使用） */
function extractCard(base64Jpeg) {
  const blob = Utilities.newBlob(Utilities.base64Decode(base64Jpeg), 'image/jpeg', 'meishi.jpg');
  // 画像を Google ドキュメントに変換すると OCR された文字が入る。読み取ったらすぐ削除する
  const file = Drive.Files.create(
    { name: '名刺OCR_一時ファイル', mimeType: 'application/vnd.google-apps.document' },
    blob,
    { ocrLanguage: 'ja' }
  );
  let text;
  try {
    text = DocumentApp.openById(file.id).getBody().getText();
  } finally {
    Drive.Files.remove(file.id);
  }
  if (!text.trim()) throw new Error('文字を読み取れませんでした。明るい場所で名刺を大きく撮り直してください');
  return parseCardText(text);
}

/** OCR した文字列を項目に振り分ける（簡易ルール。画面で確認・修正する前提） */
function parseCardText(text) {
  const card = {};
  FIELDS.forEach(f => { card[f.key] = ''; });
  let lines = text.normalize('NFKC').split(/\r?\n/).map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
  const rest = [];
  const phoneRe = /(?:\+81[-\s]?|\(?0)\d{1,4}\)?[-\s.)]?\d{1,4}[-\s.]?\d{3,4}/;

  lines.forEach(line => {
    let l = line;
    const email = l.match(/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/);
    if (email) { if (!card.email) card.email = email[0]; l = l.replace(email[0], ''); }
    const url = l.match(/(?:https?:\/\/|www\.)[^\s]+/i);
    if (url) { if (!card.url) card.url = url[0]; l = l.replace(url[0], ''); }
    if (email || url) l = l.replace(/E-?mail|Mail|URL|HP|Web/gi, '');

    // 電話・携帯・FAX（1行に複数あることもある）
    let m;
    const re = new RegExp('((?:TEL|Tel|T|電話|FAX|Fax|F|携帯|Mobile|MOBILE|M)[\\s.:：]*)?(' + phoneRe.source + ')', 'g');
    let found = false;
    while ((m = re.exec(l)) !== null) {
      const label = (m[1] || '').toUpperCase();
      const num = m[2].replace(/[\s.]/g, '-').replace(/\((\d+)\)/, '$1-').replace(/--+/g, '-');
      const digits = num.replace(/\D/g, '');
      if (digits.length < 10 || /〒/.test(l.slice(Math.max(0, m.index - 2), m.index + 1))) continue;
      found = true;
      if (/^F/.test(label)) { if (!card.fax) card.fax = num; }
      else if (/携帯|^M/.test(label) || /^(?:81)?0?[789]0/.test(digits)) { if (!card.mobile) card.mobile = num; else if (!card.phone) card.phone = num; }
      else if (!card.phone) card.phone = num;
      else if (!card.fax) card.fax = num;
    }
    if (found) l = l.replace(new RegExp(phoneRe.source, 'g'), '').replace(/(?:TEL|Tel|FAX|Fax|電話|携帯|Mobile|MOBILE)[\s.:：]*/g, '').replace(/(?:^|\s)[TFM][\s.:：]*(?=\s|$)/g, ' ');

    const postal = l.match(/〒?\s*(\d{3})-(\d{4})/);
    if (postal && !card.postal) { card.postal = postal[1] + '-' + postal[2]; l = l.replace(postal[0], ''); }

    l = l.replace(/^[\s/|:：・,]+|[\s/|:：・,]+$/g, '');
    if (l) rest.push(l);
  });

  const take = (pred, key, map) => {
    if (card[key]) return;
    const i = rest.findIndex(pred);
    if (i >= 0) card[key] = map ? map(rest[i], i) : rest.splice(i, 1)[0];
  };

  take(l => /(北海道|東京都|京都府|大阪府|.{1,3}県)\S*[市区町村郡]|[市区町村].*\d|丁目|番地/.test(l), 'address');
  take(l => /株式会社|有限会社|合同会社|合資会社|(?:一般|公益)?(?:社団|財団)法人|NPO法人|協会|組合|機構|大学|役場|市役所|町役場|\(株\)|㈱|Inc\.?|Co\.,?|Ltd|Corporation|LLC/i.test(l), 'company');

  const titleRe = /(代表取締役(?:社長)?|事務局長|局長|取締役|代表理事|理事長|理事|会長|社長|副社長|専務|常務|執行役員|支店長|支社長|本部長|部長|次長|室長|課長|係長|所長|主任|主査|主事|店長|マネージャー|マネジャー|リーダー|ディレクター|プロデューサー|CEO|COO|CTO|CFO|Manager|Director|President|担当)(?:代理|補佐)?/;
  const deptRe = /\S*(?:本部|事業部|部|課|室|局|グループ|チーム|センター|支店|営業所|Division|Department|Dept)/;
  for (let i = 0; i < rest.length && !(card.title && card.department); i++) {
    const l = rest[i];
    const t = l.match(titleRe);
    const d = !t || l.replace(t[0], '').trim() ? l.replace(t ? t[0] : '', '').trim().match(deptRe) : null;
    if (!t && !(d && l.length <= 30)) continue;
    if (t && !card.title) card.title = t[0];
    if (d && !card.department && l.length <= 40) card.department = l.replace(t ? t[0] : '', '').trim();
    rest.splice(i--, 1);
  }

  take(l => /^[ぁ-んァ-ヶー\s]{2,20}$/.test(l), 'name_kana');
  take(l => /^[一-龠々〆ヵヶぁ-んァ-ヶー]{1,5} [一-龠々〆ヵヶぁ-んァ-ヶー]{1,6}$/.test(l), 'name');
  take(l => /^[一-龠々〆ヵヶ]{2,6}$/.test(l), 'name');
  take(l => /^[A-Z][a-z]+ [A-Z][a-z]+$/.test(l) || /^[A-Z]+ [A-Z]+$/.test(l), 'name');

  card.memo = rest.join(' / ');
  return card;
}

/** 確認済みの項目をスプレッドシートの表の最初の空き行に書き込む */
function appendCard(card) {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = SHEET_NAME ? ss.getSheetByName(SHEET_NAME) : ss.getSheets()[0];
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const lastRow = Math.max(sheet.getLastRow(), 1);
    const lastCol = Math.max(sheet.getLastColumn(), 1);
    const values = sheet.getRange(1, 1, lastRow, lastCol).getDisplayValues();

    const norm = s => String(s).replace(/[\s　]/g, '').toLowerCase();
    const allAliases = [RESPONDER_ALIASES, DATE_ALIASES].concat(FIELDS.map(f => f.aliases));
    const matchCol = (headers, aliases) => {
      const a = aliases.map(norm);
      let i = headers.findIndex(h => a.indexOf(norm(h)) >= 0);
      if (i < 0) i = headers.findIndex(h => norm(h) && a.some(x => norm(h).indexOf(x) >= 0));
      return i;
    };

    // 見出し行を探す（上から30行のうち、見出し名が一番多く当てはまる行）
    let headerRow = -1, best = 1;
    for (let r = 0; r < Math.min(values.length, 30); r++) {
      const exact = allAliases.filter(a => values[r].some(h => a.map(norm).indexOf(norm(h)) >= 0)).length;
      if (exact > best) { best = exact; headerRow = r; }
    }
    if (headerRow < 0) throw new Error('見出し行（会社名・名前・対応者など）が見つかりませんでした');
    const headers = values[headerRow];

    // 列の対応を決める（同じ列に二重に入れない）
    const used = {};
    const cells = {};
    const put = (aliases, value) => {
      const i = matchCol(headers.map((h, j) => used[j] ? '' : h), aliases);
      if (i < 0) return false;
      used[i] = true;
      if (value) cells[i] = value;
      return true;
    };
    put(RESPONDER_ALIASES, RESPONDER);
    put(DATE_ALIASES, Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd'));
    if (!card.phone && card.mobile) { card.phone = card.mobile; card.mobile = ''; }
    const leftovers = [];
    FIELDS.forEach(f => {
      const v = (card[f.key] || '').trim();
      if (f.key === 'memo') return;
      if (!put(f.aliases, v) && v) leftovers.push(f.label + ': ' + v);
    });
    const memo = [(card.memo || '').trim()].concat(leftovers).filter(Boolean).join(' / ');
    if (memo) put(['メモ', '備考', 'note'], memo);

    // 表の中で、対応づけた列がすべて空いている最初の行を探す
    const cols = Object.keys(used).map(Number);
    let target = -1;
    for (let r = headerRow + 1; r < values.length; r++) {
      if (cols.every(c => values[r][c] === '')) { target = r; break; }
    }
    const rowNum = target >= 0 ? target + 1 : values.length + 1;

    // 値のある列だけ書き込む（他の列の書式・プルダウン・数式は触らない）
    Object.keys(cells).forEach(c => sheet.getRange(rowNum, Number(c) + 1).setValue(cells[c]));
    return { row: rowNum, sheet: sheet.getName() };
  } finally {
    lock.releaseLock();
  }
}
