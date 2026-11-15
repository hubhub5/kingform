/**
 * 킹율 × 메가주 신청 폼 — Google Apps Script 백엔드
 * 1) 구글 시트 새로 만들기 → 확장 프로그램 > Apps Script → 이 코드 전체 붙여넣기
 * 2) 배포 > 새 배포 > 유형: 웹 앱 / 실행: 나 / 액세스: 모든 사용자 → URL 복사
 * 3) index.html 의 CONFIG.SCRIPT_URL 에 붙여넣기
 */

const SHEET_MAIN = '신청';
const SHEET_STORY = '스토리후보';
const CODE_PREFIX = 'KY-';

const HEADERS = [
  '서버시각', '수령번호', '이름', '휴대폰', '만14세이상',
  '반려종류', '반려동물이름', '품종', '나이', '시도', '시군구', '관심주제',
  '증정박스', '한마디', '닉네임', 'SNS공개동의',
  '필수동의', '광고_문자', '광고_카카오', '동의시각', '동의문구버전',
  '오프라인임시번호', '기기시각', '행사',
];

function sheet_(name, headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.appendRow(headers);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, headers.length).setFontWeight('bold').setBackground('#2b1654').setFontColor('#ffffff');
  }
  return sh;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function clean_(v, max) {
  // 수식 주입 방지(=,+,-,@ 로 시작하는 값) + 길이 제한
  let s = String(v == null ? '' : v).slice(0, max || 100);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);
    const d = JSON.parse(e.postData.contents);
    const phone = String(d.phone || '').replace(/\D/g, '');
    if (!/^01[016789]\d{7,8}$/.test(phone)) return json_({ ok: false, error: 'phone' });
    if (!d.privacyOk || !d.age14) return json_({ ok: false, error: 'consent' });

    const sh = sheet_(SHEET_MAIN, HEADERS);
    const last = sh.getLastRow();

    // 중복 확인: 휴대폰 열(4번째)
    if (last > 1) {
      const rows = sh.getRange(2, 1, last - 1, 15).getValues();
      for (let i = 0; i < rows.length; i++) {
        if (String(rows[i][3]).replace(/\D/g, '') === phone) {
          return json_({
            ok: true, duplicate: true, code: rows[i][1], name: rows[i][2],
            petName: rows[i][6], box: rows[i][12], boxDesc: '',
          });
        }
      }
    }

    const code = CODE_PREFIX + String(last).padStart(4, '0'); // 1번째 신청 = KY-0001
    const now = new Date();
    const mkt = !!(d.mktSms || d.mktKakao);
    sh.appendRow([
      now, code, clean_(d.name, 20), "'" + phone, d.age14 ? 'Y' : 'N',
      clean_(d.species, 10), clean_(d.petName, 12), clean_(d.breed, 20), clean_(d.petAge, 10),
      clean_(d.sido, 10), clean_(d.sigungu, 20), (d.topics || []).map(t => clean_(t, 10)).join(', '),
      clean_(d.box, 4), clean_(d.message, 40), clean_(d.nick, 12), d.snsOk ? 'Y' : 'N',
      'Y', d.mktSms ? 'Y' : 'N', d.mktKakao ? 'Y' : 'N', mkt ? now : '', clean_(d.consentVersion, 30),
      clean_(d.offlineCode, 10), clean_(d.clientTime, 30), clean_(d.event, 30),
    ]);

    // 스토리 후보: 공개 동의 + 한마디 있는 경우만, 이름·번호 없이
    if (d.snsOk && d.message) {
      sheet_(SHEET_STORY, ['시각', '닉네임', '한마디', '반려동물', '올림?'])
        .appendRow([now, clean_(d.nick || '익명의 율무덕후', 12), clean_(d.message, 40),
          [d.petName, d.breed].filter(Boolean).map(v => clean_(v, 20)).join(' / '), '']);
    }

    return json_({ ok: true, duplicate: false, code: code, name: d.name, petName: d.petName, box: d.box, boxDesc: d.boxDesc });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

/** 브라우저로 URL 열었을 때 동작 확인용 */
function doGet() {
  return json_({ ok: true, msg: '킹율 폼 서버 살아있음 🐾' });
}

/** 세그먼트 집계 (Apps Script 편집기에서 직접 실행 → 로그 확인) */
function segmentReport() {
  const sh = sheet_(SHEET_MAIN, HEADERS);
  const rows = sh.getLastRow() > 1 ? sh.getRange(2, 1, sh.getLastRow() - 1, HEADERS.length).getValues() : [];
  const col = name => HEADERS.indexOf(name);
  const count = (f) => rows.filter(f).length;
  const anyAd = r => r[col('광고_문자')] === 'Y' || r[col('광고_카카오')] === 'Y';
  const topics = ['보험', '훈련·행동', '건강·병원', '사료·간식', '미용', '여행·호텔', '장난감·용품', '장례·추모'];
  const out = [
    `전체 신청: ${rows.length}`,
    `광고 수신 동의(문자 또는 카카오): ${count(anyAd)}`,
    `  └ 문자 동의: ${count(r => r[col('광고_문자')] === 'Y')} / 카카오 동의: ${count(r => r[col('광고_카카오')] === 'Y')}`,
    ...topics.map(t => `관심 ${t} (광고동의자): ${count(r => anyAd(r) && String(r[col('관심주제')]).includes(t))}`),
  ];
  Logger.log(out.join('\n'));
}
