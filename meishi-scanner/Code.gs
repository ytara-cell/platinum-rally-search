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
  { key: 'url',        label: 'URL',      aliases: ['url', 'hp', 'ホームページ', 'webサイト', 'サイト'] },
  { key: 'memo',       label: 'メモ',     aliases: ['メモ', '備考', 'note'] },
];
const RESPONDER_ALIASES = ['対応者', '対応', '営業担当'];
const DATE_ALIASES = ['日付', '登録日', '取得日', '交換日', '受付日', '日時', 'date'];

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

/** 確認済みの項目をスプレッドシートに追記する */
function appendCard(card) {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = SHEET_NAME ? ss.getSheetByName(SHEET_NAME) : ss.getSheets()[0];
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    let lastCol = sheet.getLastColumn();
    let headers = lastCol > 0 ? sheet.getRange(1, 1, 1, lastCol).getValues()[0].map(String) : [];

    // 見出しが無い空のシートなら見出し行を作る
    if (headers.every(h => h.trim() === '')) {
      headers = ['日付'].concat(FIELDS.map(f => f.label), ['対応者']);
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
      lastCol = headers.length;
    }

    const norm = s => String(s).replace(/[\s　]/g, '').toLowerCase();
    const findCol = aliases => {
      const a = aliases.map(norm);
      let i = headers.findIndex(h => a.indexOf(norm(h)) >= 0);
      if (i < 0) i = headers.findIndex(h => h && a.some(x => norm(h).indexOf(x) >= 0));
      return i;
    };

    const row = new Array(headers.length).fill('');
    const used = {};
    const put = (aliases, value) => {
      const i = findCol(aliases);
      if (i >= 0 && !used[i]) { row[i] = value; used[i] = true; return true; }
      return false;
    };

    put(RESPONDER_ALIASES, RESPONDER);
    put(DATE_ALIASES, Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd'));
    const leftovers = [];
    FIELDS.forEach(f => {
      const v = (card[f.key] || '').trim();
      if (!put(f.aliases, v) && v) leftovers.push(f.label + ': ' + v);
    });
    // 対応する列が無い項目は「メモ/備考」列にまとめる（あれば）
    if (leftovers.length) {
      const i = findCol(['メモ', '備考', 'note']);
      if (i >= 0) row[i] = [row[i]].concat(leftovers).filter(Boolean).join(' / ');
    }

    sheet.appendRow(row);
    return { row: sheet.getLastRow(), sheet: sheet.getName() };
  } finally {
    lock.releaseLock();
  }
}
