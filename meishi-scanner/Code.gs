/**
 * 名刺スキャナー
 * スマホのカメラで名刺を撮影 → Claude で項目を読み取り → 確認・修正 → スプレッドシートに追記。
 * 「対応者」列には常に RESPONDER（多良）を記入する。
 */

const SPREADSHEET_ID = '1jApTwQmymraPikdQAngU0UCyxiYi7L1bQZr9tRTzQHw';
const SHEET_NAME = ''; // 空なら先頭のシートに追記
const RESPONDER = '多良';
const MODEL = 'claude-opus-5-5';

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

/** 画像（base64 JPEG）から名刺の項目を読み取る */
function extractCard(base64Jpeg) {
  const apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) throw new Error('スクリプト プロパティに ANTHROPIC_API_KEY が設定されていません');

  const properties = {};
  FIELDS.forEach(f => { properties[f.key] = { type: 'string', description: f.label }; });

  const body = {
    model: MODEL,
    max_tokens: 4000,
    output_config: {
      effort: 'low',
      format: {
        type: 'json_schema',
        schema: {
          type: 'object',
          properties: properties,
          required: FIELDS.map(f => f.key),
          additionalProperties: false,
        },
      },
    },
    messages: [{
      role: 'user',
      content: [
        { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: base64Jpeg } },
        { type: 'text', text:
          'この名刺画像から各項目を読み取ってください。記載のない項目は空文字にしてください。' +
          '電話番号はハイフン区切り、メールアドレス・URLは半角で。' +
          'memo には他の項目に入らない情報（資格・SNSなど）があれば簡潔に入れてください。' },
      ],
    }],
  };

  const res = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', {
    method: 'post',
    contentType: 'application/json',
    headers: { 'x-api-key': apiKey, 'anthropic-version': '2023-06-01' },
    payload: JSON.stringify(body),
    muteHttpExceptions: true,
  });
  const code = res.getResponseCode();
  const json = JSON.parse(res.getContentText());
  if (code !== 200) throw new Error('読み取りに失敗しました (' + code + '): ' + (json.error && json.error.message));
  if (json.stop_reason === 'refusal') throw new Error('この画像は読み取れませんでした');

  const text = json.content.filter(b => b.type === 'text').map(b => b.text).join('');
  return JSON.parse(text);
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
