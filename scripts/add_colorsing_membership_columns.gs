/**
 * ColorSing 月次タブに「メンバーシップ関連 6 列」を追加する Google Apps Script
 * =============================================================================
 *
 * 対象スプレッドシート:
 *   ETERNALdct_ライバー管理_運用開始版
 *   https://docs.google.com/spreadsheets/d/1jaBZnxMgy6H8lpOESBWM21hGnswH0NXG3SwBOuRyTu8/edit
 *
 * やること:
 *   タブ名が "ColorSing_" で始まる月次タブ（9 枚）すべてについて、
 *   「歌推し人数」列のすぐ右に、次の 6 列を挿入して見出しを入れる。
 *
 *     1. フォロワー人数
 *     2. メンバーシップ加入人数
 *     3. メンバーシップ新規追加人数
 *     4. メンバーシップ1ヶ月
 *     5. メンバーシップ3ヶ月
 *     6. メンバーシップ6ヶ月
 *
 *   ※ 入力用ゾーンの「貼付_ColorSing進捗」タブは対象外（毎月の貼り付け位置が
 *      ずれるのを避けるため）。含めたい場合は TARGET_PREFIX の判定を変更する。
 *
 * 特徴:
 *   - 見出し行はタブごとに 3 行目 / 5 行目が混在しているため、各タブで
 *     「歌推し人数」を検索して見出し行と列位置を自動判定する。
 *   - insertColumnsAfter を使うので、既存の数式・書式・INDIRECT 参照
 *     （担当_* タブが読む C 列など）は壊れない。挿入位置は M 列より右なので
 *     C 列参照には影響しない。
 *   - 冪等（べきとう）: すでに「フォロワー人数」がある見出し行は二重追加せず
 *     スキップするので、何回実行しても安全。
 *
 * 実行手順:
 *   1. 対象スプレッドシートを開く
 *   2. 拡張機能 → Apps Script
 *   3. このファイルの中身を貼り付けて保存
 *   4. 関数 addMembershipColumns を選択して「実行」
 *      （初回は権限承認のダイアログが出るので許可する）
 *   5. 実行ログ（表示 → ログ / Execution log）で結果を確認
 */

var NEW_HEADERS = [
  'フォロワー人数',
  'メンバーシップ加入人数',
  'メンバーシップ新規追加人数',
  'メンバーシップ1ヶ月',
  'メンバーシップ3ヶ月',
  'メンバーシップ6ヶ月'
];

// 見出しの目印になる既存列
var ANCHOR_HEADER = '歌推し人数';
// 追加済み判定に使う最初の新規見出し
var GUARD_HEADER = NEW_HEADERS[0];
// 対象タブ名の接頭辞（"ColorSing_" で始まる月次タブのみ）
var TARGET_PREFIX = 'ColorSing_';
// 見出し行を探す範囲（先頭から何行目までを見るか）
var HEADER_SEARCH_ROWS = 10;

function addMembershipColumns() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  var summary = [];

  sheets.forEach(function (sheet) {
    var name = sheet.getName();
    if (name.indexOf(TARGET_PREFIX) !== 0) {
      return; // "ColorSing_" で始まらないタブは対象外
    }

    var pos = findHeaderCell(sheet, ANCHOR_HEADER);
    if (!pos) {
      summary.push('SKIP  ' + name + '（「' + ANCHOR_HEADER + '」が見つからない）');
      return;
    }

    // すでに追加済みなら何もしない（冪等）
    if (findHeaderCell(sheet, GUARD_HEADER)) {
      summary.push('SKIP  ' + name + '（追加済み）');
      return;
    }

    var headerRow = pos.row;
    var anchorCol = pos.col; // 「歌推し人数」の列（= M 列）

    // 「歌推し人数」の直後に 6 列挿入（書式は左隣＝歌推し人数列から引き継ぐ）
    sheet.insertColumnsAfter(anchorCol, NEW_HEADERS.length);

    // 見出しを書き込む
    var headerRange = sheet.getRange(headerRow, anchorCol + 1, 1, NEW_HEADERS.length);
    headerRange.setValues([NEW_HEADERS]);

    summary.push('OK    ' + name + '（' + columnLetter(anchorCol + 1) + headerRow +
                 ' から 6 列追加）');
  });

  var msg = summary.length
    ? summary.join('\n')
    : '対象タブ（' + TARGET_PREFIX + '*）が見つかりませんでした。';
  Logger.log(msg);

  // UI から実行された場合はダイアログでも結果を表示
  try {
    SpreadsheetApp.getUi().alert('メンバーシップ列の追加結果\n\n' + msg);
  } catch (e) {
    // トリガー等 UI が無い実行環境では無視
  }
}

/**
 * 指定シートの先頭数行から、text に完全一致するセルを探す。
 * 見つかれば {row, col}（1 始まり）、無ければ null。
 */
function findHeaderCell(sheet, text) {
  var maxRow = Math.min(HEADER_SEARCH_ROWS, sheet.getMaxRows());
  var maxCol = sheet.getMaxColumns();
  if (maxRow < 1 || maxCol < 1) return null;
  var values = sheet.getRange(1, 1, maxRow, maxCol).getValues();
  for (var r = 0; r < values.length; r++) {
    for (var c = 0; c < values[r].length; c++) {
      var v = values[r][c];
      if (typeof v === 'string' && v.trim() === text) {
        return { row: r + 1, col: c + 1 };
      }
    }
  }
  return null;
}

/** 列番号(1始まり)を A1 の列文字へ変換（ログ表示用）。 */
function columnLetter(col) {
  var s = '';
  while (col > 0) {
    var m = (col - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    col = Math.floor((col - 1) / 26);
  }
  return s;
}
