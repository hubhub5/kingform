/**
 * 킹율 × 메가주 신청 폼 — Google Apps Script 백엔드
 * 1) 구글 시트 → 확장 프로그램 > Apps Script → 이 코드 전체 붙여넣기 → setup 한 번 실행
 * 2) 배포 > 새 배포 > 유형: 웹 앱 / 실행: 나 / 액세스: 모든 사용자 → URL 복사
 * 3) index.html 의 CONFIG.SCRIPT_URL 에 붙여넣기
 */

const SHEET_MAIN = '신청';
const SHEET_STORY = '스토리후보';
const SHEET_SUMMARY = 'B2B요약';
const CODE_PREFIX = 'KY-';

// [헤더, payload 키, 최대 길이]  — 순서 바꿔도 됨(열 위치는 이름으로 찾음)
const COLS = [
  ['서버시각'], ['수령번호'], ['이름', 'name', 20], ['휴대폰'], ['만14세이상'], ['보호자나이대', 'ownerAge', 10],
  ['반려견이름', 'petName', 12], ['견종', 'breed', 20], ['나이', 'petAge', 10], ['성별·중성화', 'sexNeuter', 12],
  ['몸무게', 'weight', 16], ['반려견수', 'dogCount', 6],
  ['시도', 'sido', 10], ['시군구', 'sigungu', 20], ['주거형태', 'housing', 16],
  ['산책', 'walk', 12], ['혼자있는시간', 'alone', 12], ['주식', 'food', 16],
  ['건강고민', 'health', 120], ['펫보험', 'insurance', 12],
  ['관심주제', 'topics', 120], ['월지출', 'spend', 12], ['구매처', 'channels', 120],
  ['증정박스', 'box', 4], ['한마디', 'message', 40], ['닉네임', 'nick', 12], ['SNS공개동의'],
  ['필수동의'], ['광고_문자'], ['광고_카카오'], ['광고동의'], ['동의시각'], ['동의문구버전', 'consentVersion', 30],
  ['오프라인임시번호', 'offlineCode', 10], ['기기시각', 'clientTime', 30], ['행사', 'event', 30],
];
const HEADERS = COLS.map(c => c[0]);
const col_ = name => HEADERS.indexOf(name);              // 0-based
const letter_ = name => colLetter_(col_(name) + 1);

// 요약 탭에 집계할 항목 (index.html 의 선택지와 같아야 함)
const DIMS = [
  ['보호자나이대', ['10대', '20대', '30대', '40대', '50대 이상']],
  ['몸무게', ['3kg 미만', '3~7kg', '7~15kg', '15~25kg', '25kg 이상']],
  ['나이', ['1살 미만', '1~2살', '3~4살', '5~6살', '7~9살', '10살 이상']],
  ['성별·중성화', ['남아·중성화O', '남아·중성화X', '여아·중성화O', '여아·중성화X']],
  ['반려견수', ['1마리', '2마리', '3마리 이상']],
  ['주거형태', ['아파트', '빌라·오피스텔', '주택·마당']],
  ['산책', ['거의 안 해', '하루 1번', '하루 2번 이상']],
  ['혼자있는시간', ['거의 없어', '4시간 미만', '4~8시간', '8시간 이상']],
  ['주식', ['건사료', '습식·화식', '생식·동결건조', '수제·섞어서']],
  ['건강고민', ['피부·알러지', '관절·슬개골', '치아·입냄새', '눈물·눈', '소화·장', '체중·비만', '짖음·분리불안', '노견 케어', '없어 튼튼해'], true],
  ['펫보험', ['가입했어', '알아보는 중', '아직 생각 없어']],
  ['관심주제', ['보험', '훈련·행동', '건강·병원', '사료·간식', '미용', '여행·호텔', '장난감·용품', '장례·추모'], true],
  ['월지출', ['5만 원 미만', '5~10만 원', '10~20만 원', '20~30만 원', '30만 원 이상']],
  ['구매처', ['쿠팡·종합몰', '네이버쇼핑', '펫 전문몰', '브랜드 공식몰', '동물병원', '동네 펫샵'], true],
  ['시도', ['서울', '경기', '인천', '부산', '대구', '광주', '대전', '울산', '세종', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']],
];

function colLetter_(n) { let s = ''; while (n > 0) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); } return s; }

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
  if (Array.isArray(v)) v = v.map(x => String(x).slice(0, 20)).join(', ');
  let s = String(v == null ? '' : v).slice(0, max || 100);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}

/** 처음 한 번 실행: 탭 3개 만들고 요약 수식 깔기 (doPost 에서도 없으면 자동 생성) */
function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  sheet_(SHEET_MAIN, HEADERS);
  sheet_(SHEET_STORY, ['시각', '닉네임', '한마디', '반려견', '올림?']);
  if (!ss.getSheetByName(SHEET_SUMMARY)) buildSummary_();
  const def = ss.getSheetByName('시트1') || ss.getSheetByName('Sheet1');
  if (def && ss.getSheets().length > 1 && def.getLastRow() === 0) ss.deleteSheet(def);
}

/** 요약 탭 다시 만들기 (선택지 바꾼 뒤 편집기에서 실행) */
function rebuildSummary() { buildSummary_(); }

/** B2B요약 탭: 응답이 들어오면 수식이 알아서 갱신됨 */
function buildSummary_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const old = ss.getSheetByName(SHEET_SUMMARY);
  if (old) ss.deleteSheet(old);
  const sh = ss.insertSheet(SHEET_SUMMARY);
  const M = `'${SHEET_MAIN}'!`;
  const total = `COUNTA(${M}B2:B)`;
  const ad = `${M}${letter_('광고동의')}2:${letter_('광고동의')}`;
  const rows = [
    ['킹율 × 메가주 반려견 보호자 DB 요약', '', '', '', ''],
    ['전체 응답', `=${total}`, '', '광고 수신 동의', `=COUNTIF(${ad},"Y")`],
    ['', '', '', '', ''],
    ['항목', '선택지', '응답 수', '비율', '광고동의자 중'],
  ];
  const heads = [];
  DIMS.forEach(([name, opts, multi]) => {
    const L = letter_(name), rng = `${M}${L}2:${L}`;
    heads.push(rows.length + 1);
    opts.forEach((o, i) => {
      // COUNTIF 는 ~ * ? 를 특수문자로 봐서 '3~7kg' 같은 값이 안 셈 → 정확 비교/FIND 로 셈
      const hit = multi ? `ISNUMBER(FIND("${o}",${rng}))` : `(${rng}="${o}")`;
      const r = rows.length + 1;
      rows.push([i === 0 ? name : '', o, `=SUMPRODUCT(--${hit})`, `=IFERROR(C${r}/${total},0)`, `=SUMPRODUCT(--${hit},--(${ad}="Y"))`]);
    });
  });
  sh.getRange(1, 1, rows.length, 5).setValues(rows);
  sh.getRange(5, 4, rows.length - 4, 1).setNumberFormat('0.0%');
  sh.getRange(1, 1).setFontSize(14).setFontWeight('bold');
  sh.getRange(4, 1, 1, 5).setFontWeight('bold').setBackground('#2b1654').setFontColor('#ffffff');
  heads.forEach(r => sh.getRange(r, 1, 1, 5).setBorder(true, null, null, null, null, null));
  sh.getRange(5, 1, rows.length - 4, 1).setFontWeight('bold');

  // 오른쪽: 견종·동네 TOP 15
  const B = `${M}${letter_('견종')}2:${letter_('견종')}`, G = `${M}${letter_('시군구')}2:${letter_('시군구')}`, S = `${M}${letter_('시도')}2:${letter_('시도')}`;
  sh.getRange('G4:H4').setValues([['견종 TOP 15', '응답 수']]);
  sh.getRange('G5').setFormula(`=IFERROR(QUERY({${B}},"select Col1, count(Col1) where Col1 <> '' group by Col1 order by count(Col1) desc limit 15 label count(Col1) ''",0),"")`);
  sh.getRange('J4:K4').setValues([['동네 TOP 15', '응답 수']]);
  sh.getRange('J5').setFormula(`=IFERROR(QUERY({ARRAYFORMULA(IF(${S}="","",${S}&" "&${G}))},"select Col1, count(Col1) where Col1 <> '' group by Col1 order by count(Col1) desc limit 15 label count(Col1) ''",0),"")`);
  ['G4:H4', 'J4:K4'].forEach(a => sh.getRange(a).setFontWeight('bold').setBackground('#2b1654').setFontColor('#ffffff'));
  sh.setColumnWidth(1, 110); sh.setColumnWidth(2, 120); sh.setColumnWidth(7, 160); sh.setColumnWidth(10, 180);
  sh.setFrozenRows(4);
  return sh;
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);
    const d = JSON.parse(e.postData.contents);
    const phone = String(d.phone || '').replace(/\D/g, '');
    if (!/^01[016789]\d{7,8}$/.test(phone)) return json_({ ok: false, error: 'phone' });
    if (!d.privacyOk || !d.age14) return json_({ ok: false, error: 'consent' });

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = sheet_(SHEET_MAIN, HEADERS);
    if (!ss.getSheetByName(SHEET_SUMMARY)) buildSummary_();
    const last = sh.getLastRow();

    // 중복 확인: 휴대폰 열
    if (last > 1) {
      const phones = sh.getRange(2, col_('휴대폰') + 1, last - 1, 1).getValues();
      for (let i = 0; i < phones.length; i++) {
        if (String(phones[i][0]).replace(/\D/g, '') === phone) {
          const row = i + 2;
          const r = sh.getRange(row, 1, 1, HEADERS.length).getValues()[0];
          // 나중에 '동의하고 선물 받기'로 다시 보낸 경우: 동의는 추가만 하고 철회로 덮어쓰지 않음
          let sms = r[col_('광고_문자')] === 'Y', kakao = r[col_('광고_카카오')] === 'Y';
          if ((d.mktSms && !sms) || (d.mktKakao && !kakao)) {
            sms = sms || !!d.mktSms; kakao = kakao || !!d.mktKakao;
            const set = (h, v) => sh.getRange(row, col_(h) + 1).setValue(v);
            set('광고_문자', sms ? 'Y' : 'N'); set('광고_카카오', kakao ? 'Y' : 'N');
            set('광고동의', 'Y'); set('동의시각', new Date());
            set('동의문구버전', clean_(d.consentVersion, 30));
          }
          return json_({
            ok: true, duplicate: true, code: r[col_('수령번호')], name: r[col_('이름')],
            petName: r[col_('반려견이름')], box: r[col_('증정박스')], boxDesc: '', gift: sms && kakao,
          });
        }
      }
    }

    const code = CODE_PREFIX + String(last).padStart(4, '0'); // 1번째 신청 = KY-0001
    const now = new Date();
    const mkt = !!(d.mktSms || d.mktKakao);
    const fixed = {
      '서버시각': now, '수령번호': code, '휴대폰': "'" + phone, '만14세이상': d.age14 ? 'Y' : 'N',
      'SNS공개동의': d.snsOk ? 'Y' : 'N', '필수동의': 'Y',
      '광고_문자': d.mktSms ? 'Y' : 'N', '광고_카카오': d.mktKakao ? 'Y' : 'N', '광고동의': mkt ? 'Y' : 'N',
      '동의시각': mkt ? now : '',
    };
    sh.appendRow(COLS.map(([h, key, max]) => (h in fixed ? fixed[h] : clean_(d[key], max))));

    // 스토리 후보: 공개 동의 + 한마디 있는 경우만, 이름·번호 없이
    if (d.snsOk && d.message) {
      sheet_(SHEET_STORY, ['시각', '닉네임', '한마디', '반려견', '올림?'])
        .appendRow([now, clean_(d.nick || '익명의 율무덕후', 12), clean_(d.message, 40),
          [d.petName, d.breed].filter(Boolean).map(v => clean_(v, 20)).join(' / '), '']);
    }

    return json_({ ok: true, duplicate: false, code: code, name: d.name, petName: d.petName, box: d.box, boxDesc: d.boxDesc, gift: !!(d.mktSms && d.mktKakao) });
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
