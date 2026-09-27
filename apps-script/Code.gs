/**
 * 광안대교 초콜릿 체험 - 응답 저장용 Google Apps Script
 *
 * [설정 방법]
 * 1. 응답을 모을 Google 스프레드시트를 새로 만듭니다.
 * 2. 메뉴 [확장 프로그램] > [Apps Script]를 열고, 이 파일 내용을 Code.gs에 붙여넣은 뒤 저장합니다.
 * 3. 오른쪽 위 [배포] > [새 배포] > 유형 '웹 앱'을 선택합니다.
 *      - 다음 사용자 인증 정보로 실행: 나
 *      - 액세스 권한이 있는 사용자: 모든 사용자
 * 4. 권한 승인 후 표시되는 '웹 앱 URL'(https://script.google.com/macros/s/.../exec)을 복사해
 *    gwangandaegyo_chocolate_experience.html 의 SHEET_ENDPOINT 값에 넣습니다.
 * 5. 코드를 수정한 뒤에는 [배포] > [배포 관리] > 편집 > 버전 '새 버전'으로 다시 배포해야 반영됩니다.
 *
 * 응답은 '응답' 시트에 한 줄씩 쌓이며, 시트가 없으면 머리글과 함께 자동으로 만들어집니다.
 */

const SHEET_NAME = '응답';

// [payload 키, 시트 머리글, 최대 글자 수]
const FIELDS = [
  ['id', '응답ID', 60],
  ['scene', '광안리 풍경', 20],
  ['visit', '방문 경험', 20],
  ['story', '나의 광안리 이야기', 50],
  ['nickname', '닉네임', 10],
  ['buy', '구매의향', 20],
  ['expect', '가장 기대되는 점', 40],
  ['expectEtc', '기대되는 점(기타)', 30],
  ['region', '거주지', 20],
  ['age', '연령대', 10]
];

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    const data = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    lock.waitLock(10000);

    const sheet = getSheet_();
    if (data.id && isDuplicate_(sheet, String(data.id))) {
      return json_({ ok: true, duplicate: true });
    }

    const row = [new Date()].concat(FIELDS.map(([key, , max]) => clean_(data[key], max)));
    sheet.appendRow(row);
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

// 브라우저에서 웹 앱 URL을 열어 배포 상태를 확인할 때 사용
function doGet() {
  return json_({ ok: true, service: 'gwangandaegyo-chocolate' });
}

function getSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(['제출 시각'].concat(FIELDS.map(([, header]) => header)));
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, FIELDS.length + 1).setFontWeight('bold').setBackground('#1464E6').setFontColor('#ffffff');
    sheet.getRange('A:A').setNumberFormat('yyyy-mm-dd hh:mm:ss');
  }
  return sheet;
}

// 같은 응답ID가 최근 200건 안에 있으면 중복 제출로 봅니다.
function isDuplicate_(sheet, id) {
  const last = sheet.getLastRow();
  if (last < 2) return false;
  const start = Math.max(2, last - 199);
  const ids = sheet.getRange(start, 2, last - start + 1, 1).getValues();
  return ids.some(([value]) => value === id);
}

// 문자열 정리 + 길이 제한 + 수식 삽입(=, +, -, @로 시작) 방지
function clean_(value, max) {
  let text = String(value == null ? '' : value).replace(/[\r\n\t]+/g, ' ').trim();
  text = Array.from(text).slice(0, max).join('');
  return /^[=+\-@]/.test(text) ? "'" + text : text;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
